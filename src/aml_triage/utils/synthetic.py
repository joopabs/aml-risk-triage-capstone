"""Seeded synthetic frame shaped like the PaySim schema. Contains no PaySim rows.

Used by the test fixtures and by scripts/make_sample.py for the CI smoke pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]
TYPES = ["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"]


def make_synthetic_frame(
    seed: int = 0,
    n_rows: int = 600,
    n_steps: int = 72,
    n_positives: int = 12,
    plant_defects: bool = True,
) -> pd.DataFrame:
    """Synthetic transactions with a learnable 'account emptied' pattern for the positives.

    With ``plant_defects`` the frame also carries 3 exact duplicate rows and one row whose origin
    balance arithmetic is deliberately inconsistent (for profiling and cleaning tests).
    """
    rng = np.random.default_rng(seed)
    step = np.sort(rng.integers(1, n_steps + 1, size=n_rows))
    ttype = rng.choice(TYPES, size=n_rows, p=[0.35, 0.1, 0.35, 0.15, 0.05])
    amount = np.round(rng.lognormal(mean=8.0, sigma=1.2, size=n_rows), 2)
    old_org = np.round(rng.lognormal(mean=9.0, sigma=1.5, size=n_rows), 2)
    outflow = np.isin(ttype, ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT"])
    new_org = np.where(outflow, np.maximum(old_org - amount, 0.0), old_org + amount)
    old_dest = np.round(rng.lognormal(mean=9.5, sigma=1.5, size=n_rows), 2)
    new_dest = np.where(np.isin(ttype, ["TRANSFER", "CASH_OUT"]), old_dest + amount, old_dest)
    name_orig = np.array([f"C{rng.integers(10**6, 10**7)}" for _ in range(n_rows)])
    name_dest = np.array(
        [f"{'M' if t == 'PAYMENT' else 'C'}{rng.integers(10**6, 10**7)}" for t in ttype]
    )

    is_fraud = np.zeros(n_rows, dtype=np.int8)
    eligible = np.flatnonzero(np.isin(ttype, ["TRANSFER", "CASH_OUT"]))
    pos = rng.choice(eligible, size=min(n_positives, len(eligible)), replace=False)
    is_fraud[pos] = 1
    # positives empty the origin account (a learnable pattern, as in the simulator)
    amount[pos] = old_org[pos]
    new_org[pos] = 0.0
    new_dest[pos] = old_dest[pos] + amount[pos]
    is_flagged = ((ttype == "TRANSFER") & (amount > np.quantile(amount, 0.995))).astype(np.int8)

    df = pd.DataFrame(
        {
            "step": step.astype(np.int32),
            "type": pd.Categorical(ttype, categories=TYPES),
            "amount": amount.astype(np.float32),
            "nameOrig": name_orig,
            "oldbalanceOrg": old_org.astype(np.float32),
            "newbalanceOrig": np.round(new_org, 2).astype(np.float32),
            "nameDest": name_dest,
            "oldbalanceDest": old_dest.astype(np.float32),
            "newbalanceDest": np.round(new_dest, 2).astype(np.float32),
            "isFraud": is_fraud,
            "isFlaggedFraud": is_flagged,
        }
    )
    if plant_defects:
        df = pd.concat([df, df.iloc[[5, 17, 29]]], ignore_index=True)
        df.loc[0, "newbalanceOrig"] = df.loc[0, "oldbalanceOrg"] - df.loc[0, "amount"] + 500.0
    return df[EXPECTED_COLUMNS]
