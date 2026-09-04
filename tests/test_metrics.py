from __future__ import annotations

import numpy as np
import pytest

from aml_triage.evaluation.metrics import compute_metrics, expected_calibration_error, is_degenerate


def test_perfect_and_random_scores() -> None:
    y = np.array([0, 0, 0, 0, 1, 1])
    perfect = np.array([0.1, 0.2, 0.3, 0.4, 0.9, 0.8])
    m = compute_metrics(y, perfect, threshold=0.5)
    assert m["pr_auc"] == pytest.approx(1.0) and m["roc_auc"] == pytest.approx(1.0)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0 and m["fpr"] == 0.0
    assert m["confusion_matrix"] == {"tn": 4, "fp": 0, "fn": 0, "tp": 2}
    assert m["prevalence"] == pytest.approx(2 / 6)
    assert m["degenerate_scores"] is False


def test_accuracy_carries_prevalence_and_majority_baseline() -> None:
    y = np.array([0] * 99 + [1])
    m = compute_metrics(y, np.zeros(100) + 0.01, threshold=0.5)
    assert m["accuracy"] == pytest.approx(0.99)  # majority-class accuracy...
    assert m["prevalence"] == pytest.approx(0.01)  # ...is exactly 1 - prevalence: never a headline


def test_constant_scores_are_flagged_degenerate_but_metrics_still_compute() -> None:
    y = np.array([0, 1, 0, 1])
    s = np.full(4, 0.25)
    assert is_degenerate(s, 1e-9)
    m = compute_metrics(y, s)
    assert m["degenerate_scores"] is True
    assert m["roc_auc"] == 0.5
    assert np.isfinite(m["pr_auc"]) and np.isfinite(m["brier"])


def test_ece_bins() -> None:
    y = np.array([0, 0, 1, 1])
    assert expected_calibration_error(y, np.array([0.0, 0.0, 1.0, 1.0])) == pytest.approx(0.0)
    assert expected_calibration_error(y, np.array([0.5, 0.5, 0.5, 0.5])) == pytest.approx(
        0.0
    )  # mean score 0.5 == mean label 0.5
    assert expected_calibration_error(y, np.array([0.9, 0.9, 0.9, 0.9])) == pytest.approx(0.4)


def test_scores_outside_unit_interval_skip_probability_metrics() -> None:
    y = np.array([0, 1, 0, 1])
    m = compute_metrics(y, np.array([-1.0, 2.0, 0.0, 3.0]))
    assert np.isnan(m["brier"]) and np.isnan(m["ece"]) and np.isfinite(m["roc_auc"])
