"""Calibration assessment and the validation-only isotonic helper (research R-09)."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss

from aml_triage.evaluation.metrics import expected_calibration_error


def reliability_table(y, scores, n_bins: int = 10) -> list[dict[str, Any]]:
    y = np.asarray(y).astype(int)
    s = np.clip(np.asarray(scores, dtype="float64"), 0, 1)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(s, edges[1:-1], right=True), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        rows.append(
            {
                "bin": b,
                "lower": float(edges[b]),
                "upper": float(edges[b + 1]),
                "n": int(m.sum()),
                "mean_score": float(s[m].mean()) if m.any() else None,
                "observed_rate": float(y[m].mean()) if m.any() else None,
            }
        )
    return rows


def calibration_summary(y, scores) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    s = np.clip(np.asarray(scores, dtype="float64"), 0, 1)
    return {
        "brier": float(brier_score_loss(y, s)),
        "ece": expected_calibration_error(y, s),
        "reliability": reliability_table(y, s),
    }


def fit_isotonic(scores_val, y_val) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(np.asarray(scores_val, dtype="float64"), np.asarray(y_val).astype(int))
    return iso


def calibration_decision(scores_val, y_val, max_pr_auc_drop: float) -> dict[str, Any]:
    """Decide (on validation only) whether isotonic calibration is worth applying.

    Applied only if it lowers the Brier score without reducing PR-AUC by more than the tolerance.
    Isotonic is monotone, so the ranking (and Recall@K) is unchanged except for tie merging.
    """
    y = np.asarray(y_val).astype(int)
    s = np.asarray(scores_val, dtype="float64")
    iso = fit_isotonic(s, y)
    cal = iso.predict(s)
    before = {
        "brier": float(brier_score_loss(y, np.clip(s, 0, 1))),
        "pr_auc": float(average_precision_score(y, s)),
    }
    after = {
        "brier": float(brier_score_loss(y, cal)),
        "pr_auc": float(average_precision_score(y, cal)),
    }
    apply = (
        after["brier"] < before["brier"] and (before["pr_auc"] - after["pr_auc"]) <= max_pr_auc_drop
    )
    return {
        "method": "isotonic_val" if apply else "none",
        "before": before,
        "after": after,
        "applied": bool(apply),
        "chosen_on": "val",
    }
