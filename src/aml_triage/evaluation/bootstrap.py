"""Row-resampling bootstrap confidence intervals for PR-AUC and pooled Recall@K (spec FR-055)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from aml_triage.evaluation.capacity import recall_precision_at_k

warnings.filterwarnings("ignore", message="No positive class found in y_true")


def bootstrap_ci(
    preds: pd.DataFrame, k: int, period_steps: int, n_resamples: int, seed: int, alpha: float = 0.05
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = len(preds)
    y = preds["isFraud"].astype(int).to_numpy()
    pr, rk = [], []
    base = preds[["row_index", "step", "isFraud", "score"]].reset_index(drop=True)
    for _ in range(n_resamples):
        idx = rng.integers(0, n, n)
        sample = base.iloc[idx]
        ys = y[idx]
        if ys.min() == ys.max():
            continue
        pr.append(average_precision_score(ys, sample["score"].to_numpy()))
        res = recall_precision_at_k(sample.assign(row_index=np.arange(n)), k, period_steps)
        rk.append(res["recall_at_k"]["pooled"])
    lo, hi = 100 * alpha / 2, 100 * (1 - alpha / 2)
    return {
        "n_resamples": int(len(pr)),
        "level": 1 - alpha,
        "pr_auc": [float(np.percentile(pr, lo)), float(np.percentile(pr, hi))] if pr else None,
        "recall_at_k_pooled": [float(np.percentile(rk, lo)), float(np.percentile(rk, hi))]
        if rk
        else None,
        "k": int(k),
    }
