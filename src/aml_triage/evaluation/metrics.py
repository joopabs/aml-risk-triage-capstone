"""Metric suite (spec FR-004, data-model MetricSet). Accuracy is always paired with prevalence."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)


def expected_calibration_error(y: np.ndarray, scores: np.ndarray, n_bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(scores, edges[1:-1], right=True), 0, n_bins - 1)
    ece = 0.0
    n = len(scores)
    for b in range(n_bins):
        m = idx == b
        if m.any():
            ece += m.sum() / n * abs(scores[m].mean() - y[m].mean())
    return float(ece)


def is_degenerate(scores: np.ndarray, eps: float) -> bool:
    return bool(len(scores) == 0 or np.nanstd(scores) < eps or np.all(scores == scores[0]))


def compute_metrics(
    y, scores, threshold: float = 0.5, degenerate_eps: float = 1e-9
) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    s = np.asarray(scores, dtype="float64")
    prevalence = float(y.mean()) if len(y) else float("nan")
    degenerate = is_degenerate(s, degenerate_eps)
    pred = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    two_classes = y.min() != y.max()
    in_unit = bool(np.all((s >= 0) & (s <= 1)))
    return {
        "prevalence": prevalence,
        "pr_auc": float(average_precision_score(y, s)) if two_classes else float("nan"),
        "roc_auc": float(roc_auc_score(y, s))
        if two_classes and not degenerate
        else (0.5 if degenerate else float("nan")),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "brier": float(brier_score_loss(y, np.clip(s, 0, 1))) if in_unit else float("nan"),
        "ece": expected_calibration_error(y, s) if in_unit else float("nan"),
        "accuracy": float((pred == y).mean()),
        "threshold": float(threshold),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "degenerate_scores": degenerate,
        "n": int(len(y)),
    }
