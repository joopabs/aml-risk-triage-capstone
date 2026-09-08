"""Batch scoring for the optional UI (specs/002-batch-triage-ui): per-row validation, in-batch
ranking, and the clarified priority rule. Pure functions plus one orchestrator; no I/O.

Ranking uses the pipeline's keys (raw score desc, step asc, position asc, stable sort) so a batch
made of one review period ranks exactly like `python -m aml_triage queue`. `high` requires both
rank <= K and a raw score at or above the frozen threshold (compared at the operating point's stored
precision); a single valid row is not ranked and uses the score-only bands of POST /score.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pydantic import ValidationError

from aml_triage.api.schemas import (
    BatchRequest,
    BatchResponse,
    Contribution,
    Counts,
    OperatingPointOut,
    ScoredRow,
    TransactionRequest,
    ValidationIssue,
)
from aml_triage.api.service import OPERATING_POINT_DECIMALS, ScoringService
from aml_triage.constants import DISCLAIMER

ROW_FIELD = "_row"


def validate_rows(
    rows: list[Any], known_types: list[str] | None = None
) -> tuple[list[tuple[int, dict[str, Any]]], list[ValidationIssue]]:
    """Validate each row independently against TransactionRequest.

    Returns ``(valid, issues)`` where ``valid`` holds ``(input_row, request_dict)`` pairs in input
    order and ``issues`` holds one entry per failing field (a row with two bad fields appears twice
    and is skipped once).
    """
    valid: list[tuple[int, dict[str, Any]]] = []
    issues: list[ValidationIssue] = []
    for input_row, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            issues.append(
                ValidationIssue(
                    input_row=input_row,
                    field=ROW_FIELD,
                    reason="each transaction must be an object",
                )
            )
            continue
        try:
            req = TransactionRequest.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(p) for p in err.get("loc", ())) or ROW_FIELD
                issues.append(ValidationIssue(input_row=input_row, field=field, reason=err["msg"]))
            continue
        if known_types and req.type not in known_types:
            issues.append(
                ValidationIssue(
                    input_row=input_row,
                    field="type",
                    reason=f"type must be one of {known_types}",
                )
            )
            continue
        valid.append((input_row, req.model_dump()))
    return valid, issues


def rank_batch(raw_scores, steps, input_rows) -> np.ndarray:
    """1-based ranks aligned with the input order: raw score desc, step asc, position asc, stable.

    Identical keys to ``aml_triage.evaluation.capacity.rank_within_periods`` for a single period,
    with ``input_row`` in the role of ``row_index``.
    """
    df = pd.DataFrame(
        {
            "score": np.asarray(raw_scores, dtype=float),
            "step": np.asarray(steps, dtype=int),
            "input_row": np.asarray(input_rows, dtype=int),
        }
    )
    order = df.sort_values(
        ["score", "step", "input_row"], ascending=[False, True, True], kind="mergesort"
    )
    ranks = np.empty(len(df), dtype=int)
    ranks[order.index.to_numpy()] = np.arange(1, len(df) + 1)
    return ranks


def assign_batch_priority(
    rank: int | None,
    raw_score: float,
    primary_k: int,
    threshold: float,
    decimals: int = OPERATING_POINT_DECIMALS,
) -> str:
    """Clarified batch rule (spec FR-020)."""
    score = round(float(raw_score), decimals)
    if rank is not None and rank <= int(primary_k) and score >= float(threshold):
        return "high"
    if score >= float(threshold):
        return "medium"
    return "low"


def score_batch(service: ScoringService, req: BatchRequest) -> BatchResponse:
    """Validate, score, rank, band, and explain a batch through the single scoring path."""
    valid, issues = validate_rows(req.transactions, service.known_types)
    primary_k = int(service.op["primary_k"])
    threshold = float(service.op["threshold"])

    rows_out: list[ScoredRow] = []
    ranked = len(valid) >= 2
    if valid:
        input_rows = np.array([i for i, _ in valid], dtype=int)
        requests = [r for _, r in valid]
        steps = np.array([int(r["step"]) for r in requests], dtype=int)
        raw, display, X = service.score_many(requests)
        if ranked:
            ranks: list[int | None] = [int(r) for r in rank_batch(raw, steps, input_rows)]
            priorities = [
                assign_batch_priority(rk, s, primary_k, threshold)
                for rk, s in zip(ranks, raw, strict=True)
            ]
        else:
            ranks = [None]
            priorities = [service.priority(float(raw[0]))]
        for j, input_row in enumerate(input_rows):
            want_factors = req.explain == "all" or (
                req.explain == "high" and priorities[j] == "high"
            )
            factors = service.explain_row(X, j) if want_factors else []
            rows_out.append(
                ScoredRow(
                    input_row=int(input_row),
                    rank=ranks[j],
                    risk_score=float(display[j]),
                    review_priority=priorities[j],
                    top_contributing_features=[Contribution(**f) for f in factors],
                )
            )
        rows_out.sort(key=lambda r: (r.rank if r.rank is not None else 0, r.input_row))

    skipped_rows = {i.input_row for i in issues}
    counts = Counts(
        received=len(req.transactions),
        scored=len(valid),
        skipped=len(skipped_rows),
        high=sum(r.review_priority == "high" for r in rows_out),
        medium=sum(r.review_priority == "medium" for r in rows_out),
        low=sum(r.review_priority == "low" for r in rows_out),
    )
    return BatchResponse(
        model_version=service.version,
        operating_point=OperatingPointOut(primary_k=primary_k, threshold=threshold),
        batch_limit=service.batch_limit,
        ranked=ranked,
        counts=counts,
        rows=rows_out,
        skipped=issues,
        disclaimer=DISCLAIMER,
    )
