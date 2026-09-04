from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aml_triage.evaluation.capacity import (
    assign_periods,
    capacity_suite,
    queue_for_period,
    rank_within_periods,
    recall_precision_at_k,
)
from aml_triage.models.comparators import random_rank, rule_rank


def _frame() -> pd.DataFrame:
    # two periods of 24 steps; period 0 has 6 rows / 2 positives, period 1 has 3 rows / 1 positive,
    # period 2 has 2 rows / 0 positives
    return pd.DataFrame(
        {
            "row_index": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "step": [1, 2, 3, 4, 5, 6, 25, 26, 27, 49, 50],
            "isFraud": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            "score": [0.9, 0.9, 0.5, 0.5, 0.1, 0.1, 0.2, 0.8, 0.2, 0.3, 0.3],
        }
    )


def test_periods_and_deterministic_tie_break() -> None:
    df = _frame()
    assert assign_periods(df["step"], 24).tolist() == [0] * 6 + [1] * 3 + [2] * 2
    ranked = rank_within_periods(df, 24).set_index("row_index")
    # ties on score resolved by earlier step, then lower row_index
    assert ranked.loc[0, "rank"] == 1 and ranked.loc[1, "rank"] == 2
    assert ranked.loc[2, "rank"] == 3 and ranked.loc[3, "rank"] == 4
    again = rank_within_periods(df.sample(frac=1, random_state=3), 24).set_index("row_index")
    assert (again["rank"].sort_index() == ranked["rank"].sort_index()).all()


def test_recall_precision_at_k_and_short_period() -> None:
    res = recall_precision_at_k(_frame(), k=4, review_period_steps=24)
    p0, p1, p2 = res["per_period"]
    assert p0["hits"] == 2 and p0["recall_at_k"] == 1.0 and p0["precision_at_k"] == 0.5
    assert p1["k_effective"] == 3 and p1["shortfall"] == 1 and p1["recall_at_k"] == 1.0
    assert p2["n_positives"] == 0 and p2["recall_at_k"] is None
    assert res["periods_with_zero_positives"] == 1
    assert res["recall_at_k"]["mean_over_periods"] == 1.0  # zero-positive period excluded
    assert res["recall_at_k"]["pooled"] == pytest.approx(3 / 3)
    assert res["precision_at_k"]["pooled"] == pytest.approx(3 / (4 + 3 + 2))


def test_capacity_binds_when_k_smaller_than_positives() -> None:
    res = recall_precision_at_k(_frame(), k=1, review_period_steps=24)
    assert res["per_period"][0]["hits"] == 1 and res["per_period"][0]["recall_at_k"] == 0.5


def test_capacity_suite_over_k_grid() -> None:
    suite = capacity_suite(_frame(), [1, 4], 24)
    assert set(suite) == {"1", "4"} and suite["4"]["recall_at_k"]["pooled"] == 1.0


def test_queue_for_period_has_rank_and_shortfall() -> None:
    q = queue_for_period(_frame(), period_index=1, k=5, review_period_steps=24)
    assert len(q) == 3 and q["rank"].tolist() == [1, 2, 3] and q.iloc[0]["row_index"] == 7


def test_comparators_deterministic() -> None:
    meta = pd.DataFrame({"isFlaggedFraud": [0, 1, 0, 0], "row_index": range(4)})
    amount = pd.Series([10.0, 5.0, 100.0, 50.0])
    a, b = random_rank(meta, 42), random_rank(meta, 42)
    assert np.array_equal(a.to_numpy(), b.to_numpy()) and not np.array_equal(
        a.to_numpy(), random_rank(meta, 7).to_numpy()
    )
    r = rule_rank(meta, amount)
    assert r.idxmax() == 1  # flagged row first regardless of amount
    assert r.drop(1).idxmax() == 2  # then largest amount
    assert (r >= 0).all() and (r < 2).all()
