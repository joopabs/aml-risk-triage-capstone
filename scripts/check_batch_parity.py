"""Developer-only parity check (specs/002-batch-triage-ui, task T013 / SC-003).

Loads the transactions of review period 0 from the local test split, posts them to the batch endpoint
in one in-process request, and compares the top-K set, order, and priorities with the pipeline's
`reports/review_queue_period_0.md`. Reads data/processed (never in CI); refuses to run when the
processed data is absent. No file is written.

Usage: python scripts/check_batch_parity.py [--period 0] [--report reports/review_queue_period_0.md]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
AGG = [
    "orig_prior_txn_count",
    "orig_prior_amount_sum",
    "dest_prior_txn_count",
    "dest_prior_amount_sum",
]


def load_period_rows(period: int) -> pd.DataFrame:
    from aml_triage.config import load
    from aml_triage.evaluation.capacity import assign_periods

    cfg = load("configs/base.yaml")
    raw = pd.read_parquet(PROCESSED / "test.parquet")
    eng = pd.read_parquet(PROCESSED / "features_primary_test.parquet").rename(
        columns={"meta_row_index": "row_index"}
    )
    keep = [c for c in ["row_index", "dest_is_merchant", *AGG] if c in eng.columns]
    df = raw.merge(eng[keep], on="row_index", how="inner")
    df["period"] = assign_periods(df["step"], cfg.review.review_period_steps)
    periods = sorted(df["period"].unique())
    df = df[df["period"] == periods[period]].sort_values(["step", "row_index"], kind="mergesort")
    return df.reset_index(drop=True)


def to_requests(df: pd.DataFrame) -> list[dict]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            {
                "step": int(r.step),
                "type": str(r.type),
                "amount": float(r.amount),
                "oldbalanceOrg": float(r.oldbalanceOrg),
                "newbalanceOrig": float(r.newbalanceOrig),
                "oldbalanceDest": float(r.oldbalanceDest),
                "newbalanceDest": float(r.newbalanceDest),
                **{
                    a: (float(getattr(r, a)) if "sum" in a else int(getattr(r, a)))
                    for a in AGG
                    if hasattr(r, a)
                },
                "dest_is_merchant": bool(
                    getattr(r, "dest_is_merchant", str(r.nameDest).startswith("M"))
                ),
            }
        )
    return rows


def parse_report(path: Path) -> list[tuple[int, str]]:
    """(row_index, review_priority) for each queue row in the report, in rank order."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(
            r"\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|\s*\d+\s*\|\s*\w+\s*\|\s*[\d.]+\s*\|\s*(high|medium|low)\s*\|",
            line,
        )
        if m:
            out.append((int(m.group(2).replace(",", "")), m.group(3)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--period", type=int, default=0)
    ap.add_argument("--report", default="reports/review_queue_period_0.md")
    a = ap.parse_args()
    if (
        not (PROCESSED / "test.parquet").exists()
        or not (PROCESSED / "features_primary_test.parquet").exists()
    ):
        print(
            "refusing to run: data/processed/test.parquet and features_primary_test.parquet are required (developer machine only)",
            file=sys.stderr,
        )
        return 4
    df = load_period_rows(a.period)
    rows = to_requests(df)
    os.environ["AML_BATCH_LIMIT"] = str(len(rows))  # this check sends a whole period at once

    from fastapi.testclient import TestClient

    from aml_triage.api.main import create_app

    with TestClient(create_app("models")) as c:
        cfg = c.get("/triage-config").json()
        r = c.post("/score-batch", json={"transactions": rows, "explain": "none"})
        r.raise_for_status()
        body = r.json()
    k = int(cfg["primary_k"])
    ranked = sorted(body["rows"], key=lambda x: x["rank"])[:k]
    batch_top = [
        (int(df.loc[x["input_row"] - 1, "row_index"]), x["review_priority"]) for x in ranked
    ]
    report_top = parse_report(Path(a.report))[:k]

    same_order = batch_top == report_top
    set_diff = {ri for ri, _ in batch_top} ^ {ri for ri, _ in report_top}
    prio_diff = sum(
        1
        for (ra, pa), (rb, pb) in zip(batch_top, report_top, strict=False)
        if ra == rb and pa != pb
    )
    print(
        f"period {a.period}: {len(rows):,} rows posted; model {body['model_version']}; K={k}; scored={body['counts']['scored']} skipped={body['counts']['skipped']}"
    )
    print(
        f"top-K set differences: {len(set_diff)} | order identical: {same_order} | priority differences on shared rows: {prio_diff}"
    )
    print(
        f"batch bands over the whole period: high={body['counts']['high']} medium={body['counts']['medium']} low={body['counts']['low']}"
    )
    ok = not set_diff and same_order and prio_diff == 0
    print("PARITY OK" if ok else "PARITY MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
