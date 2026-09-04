from __future__ import annotations

import numpy as np
import pandas as pd

from aml_triage.features.aggregates import (
    AGGREGATE_SPECS,
    brute_force_aggregates,
    causal_aggregates,
)
from tests.conftest import make_fixture_frame


def _small_with_repeats(seed: int = 3) -> pd.DataFrame:
    df = make_fixture_frame(seed=seed, n_rows=150, n_steps=12).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    # force repeated identifiers so aggregates are non-trivial
    df["nameOrig"] = rng.choice([f"C{i}" for i in range(20)], size=len(df))
    df["nameDest"] = rng.choice([f"C{i}" for i in range(10)] + ["M1", "M2"], size=len(df))
    df["row_index"] = df.index.to_numpy()
    return df


def test_vectorized_equals_brute_force() -> None:
    df = _small_with_repeats()
    fast = causal_aggregates(df)
    slow = brute_force_aggregates(df)
    for col in AGGREGATE_SPECS:
        np.testing.assert_allclose(
            fast[col].to_numpy(), slow[col].to_numpy(), rtol=1e-9, atol=1e-6, err_msg=col
        )


def test_row_never_sees_itself_or_future() -> None:
    df = _small_with_repeats(seed=7)
    # shuffle file order to prove ordering is by (step, row_index), not by position
    shuffled = df.sample(frac=1.0, random_state=1)
    fast = causal_aggregates(shuffled).loc[df.index]
    slow = brute_force_aggregates(df)
    np.testing.assert_allclose(
        fast["dest_prior_txn_count"].to_numpy(), slow["dest_prior_txn_count"].to_numpy()
    )
    first_rows = df.sort_values(["step", "row_index"]).groupby("nameOrig").head(1).index
    assert (fast.loc[first_rows, "orig_prior_txn_count"] == 0).all()
    assert (fast.loc[first_rows, "orig_prior_amount_sum"] == 0).all()


def test_identifiers_absent_from_output() -> None:
    out = causal_aggregates(_small_with_repeats())
    assert not ({"nameOrig", "nameDest"} & set(out.columns))
    assert set(out.columns) == set(AGGREGATE_SPECS)
