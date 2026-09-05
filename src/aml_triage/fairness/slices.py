"""Operational error-slice analysis (spec FR-073). Slices are non-protected operational partitions;
the analysis is labelled exactly as configured and must never be described as demographic fairness."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

from aml_triage.config import Config
from aml_triage.data.split import load_split
from aml_triage.evaluation.capacity import rank_within_periods

BAND_LABELS = ["very low", "low", "mid", "high", "very high"]


def fit_bands(train: pd.DataFrame) -> dict[str, np.ndarray]:
    """Quantile edges fitted on the TRAINING split (never on validation or test)."""
    amt = train["amount"].astype("float64")
    bal = train["oldbalanceOrg"].astype("float64")
    return {
        "amount_band": np.quantile(amt, [0.2, 0.4, 0.6, 0.8]),
        "orig_balance_band": np.quantile(
            bal[bal > 0], [0.25, 0.5, 0.75]
        ),  # zero balances form their own band
    }


def assign_slices(
    df: pd.DataFrame, bands: dict[str, np.ndarray], period_steps: int
) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["type"] = df["type"].astype(str)
    out["amount_band"] = pd.Series(
        np.digitize(df["amount"].astype("float64"), bands["amount_band"]), index=df.index
    ).map(dict(enumerate(BAND_LABELS)))
    bal = df["oldbalanceOrg"].astype("float64")
    b = np.where(bal <= 0, 0, 1 + np.digitize(bal, bands["orig_balance_band"]))
    out["orig_balance_band"] = pd.Series(b, index=df.index).map(
        {0: "zero", 1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
    )
    out["step_band"] = "day " + (((df["step"].astype("int64") - 1) // period_steps) + 1).astype(str)
    return out


def slice_analysis(cfg: Config, preds: pd.DataFrame, op: dict[str, Any]) -> dict[str, Any]:
    """``preds`` must carry row_index, step, isFraud, score (raw) and calibrated_score."""
    processed = cfg.paths.processed_dir
    bands = fit_bands(load_split(processed, "train")[["amount", "oldbalanceOrg"]])
    raw_test = load_split(processed, "test")[
        ["row_index", "amount", "oldbalanceOrg", "type", "step"]
    ]
    df = preds.merge(raw_test, on=["row_index", "step"], how="left", suffixes=("", "_raw"))
    if "type" not in df.columns:
        df["type"] = df["type_raw"]
    ranked = rank_within_periods(
        df[["row_index", "step", "isFraud", "score"]], cfg.review.review_period_steps
    )
    df = df.merge(ranked[["row_index", "rank", "period"]], on="row_index", how="left")
    K = int(op["primary_k"])
    thr = float(op["threshold"])
    df["in_topk"] = df["rank"] <= K
    df["flag"] = df["score"] >= thr
    sl = assign_slices(df, bands, cfg.review.review_period_steps)
    y = df["isFraud"].astype(int)
    results: dict[str, list[dict[str, Any]]] = {}
    for dim in cfg.fairness.slice_dimensions:
        rows = []
        for value, idx in sl.groupby(dim, observed=True).groups.items():
            g = df.loc[idx]
            yy = y.loc[idx]
            pos = int(yy.sum())
            n = int(len(g))
            hits = int((g["in_topk"] & (yy == 1)).sum())
            topk_n = int(g["in_topk"].sum())
            fn = int(((~g["flag"]) & (yy == 1)).sum())
            fp = int((g["flag"] & (yy == 0)).sum())
            rows.append(
                {
                    "slice": str(value),
                    "n": n,
                    "positives": pos,
                    "prevalence": pos / n if n else None,
                    "recall_at_k": hits / pos if pos else None,
                    "precision_at_k": hits / topk_n if topk_n else None,
                    "fnr_at_threshold": fn / pos if pos else None,
                    "fpr_at_threshold": fp / (n - pos) if (n - pos) else None,
                    "brier_calibrated": float(
                        brier_score_loss(yy, np.clip(g["calibrated_score"], 0, 1))
                    )
                    if n
                    else None,
                }
            )
        results[dim] = sorted(rows, key=lambda r: r["slice"])
    return {
        "label": cfg.fairness.label,
        "dimensions": list(cfg.fairness.slice_dimensions),
        "primary_k": K,
        "threshold": thr,
        "bands_fitted_on": "train",
        "band_edges": {k: [float(x) for x in v] for k, v in bands.items()},
        "results": results,
    }
