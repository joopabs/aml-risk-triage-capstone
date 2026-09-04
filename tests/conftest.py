"""Shared fixtures. The synthetic frame mimics the expected PaySim schema but contains no PaySim rows."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

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


def make_fixture_frame(
    seed: int = 0, n_rows: int = 600, n_steps: int = 72, n_positives: int = 12
) -> pd.DataFrame:
    """Small synthetic frame with several time steps, a few positives, 3 exact duplicates,
    and one row whose origin balance arithmetic is deliberately inconsistent."""
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
    is_fraud[rng.choice(eligible, size=min(n_positives, len(eligible)), replace=False)] = 1
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
    # deliberate quality defects for profiling and cleaning tests
    df = pd.concat([df, df.iloc[[5, 17, 29]]], ignore_index=True)  # 3 exact duplicates
    df.loc[0, "newbalanceOrig"] = df.loc[0, "oldbalanceOrg"] - df.loc[0, "amount"] + 500.0
    return df[EXPECTED_COLUMNS]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def base_config_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "base.yaml"


@pytest.fixture
def fixture_frame() -> pd.DataFrame:
    return make_fixture_frame()
