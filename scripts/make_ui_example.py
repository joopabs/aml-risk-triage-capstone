"""Generate the synthetic example batch shipped with the optional UI (spec FR-005, task T021).

Rows come from the project's own synthetic generator (never from the PaySim file) plus two
hand-written drained-account rows that exercise the positive pattern. Writes
deployment/ui/example_batch.csv and the identical contract example.

Usage: python scripts/make_ui_example.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aml_triage.utils.synthetic import make_synthetic_frame

OUT = [
    Path("deployment/ui/example_batch.csv"),
    Path("specs/002-batch-triage-ui/contracts/examples/example_batch.csv"),
]
RAW = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
]
MONEY = ["amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"]


def build() -> pd.DataFrame:
    df = make_synthetic_frame(seed=7, n_rows=400, n_steps=48, n_positives=8, plant_defects=False)
    pick = pd.concat(
        [df[df.isFraud == 0].sample(8, random_state=7), df[df.isFraud == 1].head(2)]
    ).sort_values("step", kind="mergesort")
    out = pick[RAW].copy()
    for c in MONEY:
        out[c] = out[c].astype("float64").round(2)
    out["orig_prior_txn_count"] = 0
    out["orig_prior_amount_sum"] = 0.0
    out["dest_prior_txn_count"] = 0
    out["dest_prior_amount_sum"] = 0.0
    out["dest_is_merchant"] = pick["nameDest"].astype(str).str.startswith("M").to_numpy()
    drained = pd.DataFrame(
        [
            dict(
                step=600,
                type="TRANSFER",
                amount=250000.0,
                oldbalanceOrg=250000.0,
                newbalanceOrig=0.0,
                oldbalanceDest=0.0,
                newbalanceDest=250000.0,
                orig_prior_txn_count=0,
                orig_prior_amount_sum=0.0,
                dest_prior_txn_count=0,
                dest_prior_amount_sum=0.0,
                dest_is_merchant=False,
            ),
            dict(
                step=600,
                type="CASH_OUT",
                amount=181000.0,
                oldbalanceOrg=181000.0,
                newbalanceOrig=0.0,
                oldbalanceDest=21182.0,
                newbalanceDest=202182.0,
                orig_prior_txn_count=0,
                orig_prior_amount_sum=0.0,
                dest_prior_txn_count=0,
                dest_prior_amount_sum=0.0,
                dest_is_merchant=False,
            ),
        ]
    )
    return pd.concat([out, drained], ignore_index=True)


def main() -> int:
    frame = build()
    text = frame.to_csv(index=False)
    for p in OUT:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"wrote {p} ({len(frame)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
