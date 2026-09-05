from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aml_triage.explain.captions import local_caption
from aml_triage.explain.pdp_ice import validity
from aml_triage.fairness.demographic import demographic_metrics
from tests.test_vocabulary import _load_vocab, find_prohibited


def test_demographic_metrics_hand_computed() -> None:
    # group A: 4 rows, 2 positives; predicted positive for 2 (1 TP, 1 FP) -> sel 0.5, TPR 0.5, FPR 0.5
    # group B: 4 rows, 2 positives; predicted positive for 1 (1 TP) -> sel 0.25, TPR 0.5, FPR 0.0
    y = [1, 1, 0, 0, 1, 1, 0, 0]
    pred = [1, 0, 1, 0, 1, 0, 0, 0]
    g = ["A"] * 4 + ["B"] * 4
    m = demographic_metrics(y, pred, g)
    assert m["per_group"]["A"]["selection_rate"] == pytest.approx(0.5)
    assert m["per_group"]["B"]["selection_rate"] == pytest.approx(0.25)
    assert m["demographic_parity_difference"] == pytest.approx(0.25)
    assert m["equalized_odds_difference"] == pytest.approx(0.5)  # FPR gap 0.5 dominates TPR gap 0
    assert m["disparate_impact_ratio"] == pytest.approx(0.5)


def test_local_caption_has_no_prohibited_language() -> None:
    cap = local_caption(
        [
            ("amount_to_orig_balance_ratio", 0.99, 2.3),
            ("type_TRANSFER", 1.0, 1.1),
            ("orig_zero_after_flag", 1, -0.4),
        ],
        0.98,
        1,
        "test review period 1",
    )
    assert (
        "raised the risk score" in cap
        and "lowered the risk score" in cap
        and "not a finding" in cap
    )
    assert find_prohibited(cap, _load_vocab()) == []


def test_pdp_validity_flags_correlated_pairs() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=500)
    X = pd.DataFrame(
        {
            "a": a,
            "b": a * 2 + rng.normal(scale=0.01, size=500),
            "c": rng.normal(size=500),
            "flag": (a > 0).astype(int),
        }
    )
    checks = {c["feature"]: c for c in validity(X, ["a", "b", "c", "flag"])}
    assert (
        checks["a"]["status"] == "omitted"
        and checks["b"]["status"] == "omitted"
        and "permutation importance" in checks["a"]["alternative"]
    )
    assert checks["c"]["status"] == "produced"
    assert checks["flag"]["status"] in {
        "produced",
        "omitted",
    }  # flag is ~0.8 correlated with a; either outcome is documented
