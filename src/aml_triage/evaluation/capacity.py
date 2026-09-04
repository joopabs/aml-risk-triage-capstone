"""Recall@K / Precision@K per review period and the review-queue ranking (research R-10, spec FR-003).

Period index = (step - 1) // review_period_steps, i.e. the simulated day. Ranking within a period:
score descending, step ascending, row_index ascending. k_effective = min(K, rows in period).
Recall@K is null for a period with no positives and excluded from the mean; pooled figures sum hits
over periods divided by total positives (recall) or total k_effective (precision).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

RANK_COLUMNS = ["row_index", "step", "isFraud", "score"]


def assign_periods(step: pd.Series, review_period_steps: int) -> pd.Series:
    return ((step.astype("int64") - 1) // int(review_period_steps)).astype("int64")


def rank_within_periods(df: pd.DataFrame, review_period_steps: int) -> pd.DataFrame:
    """Return a copy with ``period`` and 1-based ``rank`` columns (deterministic tie-break)."""
    out = df.copy()
    out["period"] = assign_periods(out["step"], review_period_steps)
    out = out.sort_values(
        ["period", "score", "step", "row_index"],
        ascending=[True, False, True, True],
        kind="mergesort",
    )
    out["rank"] = out.groupby("period").cumcount() + 1
    return out


def recall_precision_at_k(df: pd.DataFrame, k: int, review_period_steps: int) -> dict[str, Any]:
    ranked = df if "rank" in df.columns else rank_within_periods(df, review_period_steps)
    per_period: list[dict[str, Any]] = []
    for period, g in ranked.groupby("period", sort=True):
        n_rows = int(len(g))
        n_pos = int(g["isFraud"].sum())
        k_eff = min(int(k), n_rows)
        hits = int(g.loc[g["rank"] <= k_eff, "isFraud"].sum())
        per_period.append(
            {
                "period_index": int(period),
                "step_range": [int(g["step"].min()), int(g["step"].max())],
                "n_rows": n_rows,
                "n_positives": n_pos,
                "k_effective": k_eff,
                "shortfall": int(k) - k_eff,
                "hits": hits,
                "recall_at_k": (hits / n_pos) if n_pos else None,
                "precision_at_k": (hits / k_eff) if k_eff else None,
            }
        )
    recalls = [p["recall_at_k"] for p in per_period if p["recall_at_k"] is not None]
    precisions = [p["precision_at_k"] for p in per_period if p["precision_at_k"] is not None]
    total_pos = sum(p["n_positives"] for p in per_period)
    total_k = sum(p["k_effective"] for p in per_period)
    total_hits = sum(p["hits"] for p in per_period)
    return {
        "k": int(k),
        "recall_at_k": {
            "mean_over_periods": float(np.mean(recalls)) if recalls else None,
            "pooled": (total_hits / total_pos) if total_pos else None,
        },
        "precision_at_k": {
            "mean_over_periods": float(np.mean(precisions)) if precisions else None,
            "pooled": (total_hits / total_k) if total_k else None,
        },
        "periods": len(per_period),
        "periods_with_zero_positives": sum(1 for p in per_period if p["n_positives"] == 0),
        "per_period": per_period,
    }


def capacity_suite(df: pd.DataFrame, k_grid: list[int], review_period_steps: int) -> dict[str, Any]:
    ranked = rank_within_periods(df, review_period_steps)
    return {str(k): recall_precision_at_k(ranked, k, review_period_steps) for k in k_grid}


def queue_for_period(
    df: pd.DataFrame, period_index: int, k: int, review_period_steps: int
) -> pd.DataFrame:
    ranked = rank_within_periods(df, review_period_steps)
    q = ranked[ranked["period"] == period_index]
    return q[q["rank"] <= min(int(k), len(q))].copy()
