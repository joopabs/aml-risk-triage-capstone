"""Demographic fairness metrics (spec FR-071). Executed only when valid sensitive-group labels exist."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _rates(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    pos = y_true == 1
    return {
        "selection_rate": float(y_pred.mean()) if len(y_pred) else float("nan"),
        "tpr": float(y_pred[pos].mean()) if pos.any() else float("nan"),
        "fpr": float(y_pred[~pos].mean()) if (~pos).any() else float("nan"),
        "n": int(len(y_true)),
    }


def demographic_metrics(y_true, y_pred, group) -> dict[str, Any]:
    """Demographic parity difference, equalized odds difference, disparate impact ratio across groups."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    group = pd.Series(np.asarray(group))
    per = {
        str(g): _rates(y_true[group.to_numpy() == g], y_pred[group.to_numpy() == g])
        for g in sorted(group.unique(), key=str)
    }
    sel = [v["selection_rate"] for v in per.values()]
    tpr = [v["tpr"] for v in per.values() if v["tpr"] == v["tpr"]]
    fpr = [v["fpr"] for v in per.values() if v["fpr"] == v["fpr"]]
    return {
        "per_group": per,
        "demographic_parity_difference": float(max(sel) - min(sel)),
        "equalized_odds_difference": float(
            max(max(tpr) - min(tpr) if tpr else 0.0, max(fpr) - min(fpr) if fpr else 0.0)
        ),
        "disparate_impact_ratio": float(min(sel) / max(sel)) if max(sel) > 0 else float("nan"),
    }
