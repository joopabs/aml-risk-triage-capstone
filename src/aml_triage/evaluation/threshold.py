"""Operating point chosen on validation only (spec FR-044, research R-09, data-model §8).

Order of operations: pick the validation-selected candidate on the headline feature set → decide
isotonic calibration on validation → choose the F2-maximising threshold on (calibrated) validation
scores → record the K-th ranked score cutoff → write ``configs/operating_point.yaml``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import precision_recall_curve

from aml_triage.config import Config
from aml_triage.evaluation.calibration import calibration_decision, fit_isotonic
from aml_triage.evaluation.capacity import rank_within_periods
from aml_triage.evaluation.compare import collect, selection_ranking
from aml_triage.utils.io import save_joblib

PRIORITY_RULE = {"high": "rank_le_k", "medium": "above_threshold", "low": "below_threshold"}


def f2_threshold(y, scores) -> tuple[float, float]:
    """Threshold maximising F2 (recall-weighted) on the given scores."""
    prec, rec, thr = precision_recall_curve(y, scores)
    prec, rec = prec[:-1], rec[:-1]
    f2 = np.where((4 * prec + rec) > 0, 5 * prec * rec / (4 * prec + rec), 0.0)
    i = int(np.argmax(f2))
    return float(thr[i]), float(f2[i])


def k_score_cutoff(preds: pd.DataFrame, k: int, period_steps: int) -> float:
    """Median over validation periods of the K-th ranked score (the score needed to enter the queue)."""
    ranked = rank_within_periods(preds[["row_index", "step", "isFraud", "score"]], period_steps)
    kth = (
        ranked[ranked["rank"] == min(k, ranked.groupby("period")["rank"].max().min())]
        .groupby("period")["score"]
        .first()
    )
    return float(kth.median())


def choose_operating_point(cfg: Config, headline_set: str | None = None) -> dict[str, Any]:
    headline_set = headline_set or cfg.features.default_set
    runs = collect(cfg, "val")
    if not runs:
        raise FileNotFoundError("no validation runs; run `train --split val` first")
    ranking = selection_ranking(cfg, runs, headline_set)
    selected = ranking[0]["run_id"]
    preds = runs[selected]["preds"]
    y = preds["isFraud"].astype(int).to_numpy()
    raw = preds["score"].to_numpy()

    decision = (
        calibration_decision(raw, y, cfg.calibration.max_pr_auc_drop)
        if cfg.calibration.method == "isotonic_val"
        else {"method": "none", "applied": False, "chosen_on": "val"}
    )
    calibrator_path = None
    scores = raw
    if decision.get("applied"):
        iso = fit_isotonic(raw, y)
        scores = iso.predict(raw)
        calibrator_path = str(
            save_joblib(
                iso, Path(cfg.paths.models_dir) / "runs" / selected / "calibrator_isotonic.joblib"
            )
        )

    thr, f2 = f2_threshold(y, scores)
    cal_preds = preds.assign(score=scores)
    cutoff = k_score_cutoff(cal_preds, cfg.review.primary_k, cfg.review.review_period_steps)
    op = {
        "selected_run": selected,
        "candidate_id": runs[selected]["candidate_id"],
        "feature_set": runs[selected]["feature_set"],
        "selection_basis": "validation metrics only (see reports/selection_matrix.md)",
        "primary_k": cfg.review.primary_k,
        "threshold": round(thr, 6),
        "threshold_rule": "f2_max_on_val",
        "threshold_f2": round(f2, 4),
        "priority_rule": PRIORITY_RULE,
        "k_score_cutoff": round(cutoff, 6),
        "calibration": {
            "method": decision["method"],
            "applied": bool(decision.get("applied")),
            "decision_log": decision,
            "calibrator_path": calibrator_path,
        },
        "chosen_on": "val",
        "chosen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "frozen_at": None,
        "config_hash": cfg.config_hash(),
    }
    Path(cfg.operating_point_path).write_text(
        "# Written by `python -m aml_triage choose-operating-point` (validation only).\n"
        + yaml.safe_dump(op, sort_keys=False),
        encoding="utf-8",
    )
    return op


def load_operating_point(cfg: Config) -> dict[str, Any] | None:
    p = Path(cfg.operating_point_path)
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def apply_operating_point(op: dict[str, Any], preds: pd.DataFrame) -> pd.DataFrame:
    """Return predictions with calibrated ``score`` (if a calibrator exists) and ``review_priority``."""
    out = preds.copy()
    cal_path = (op.get("calibration") or {}).get("calibrator_path")
    if cal_path and Path(cal_path).exists():
        import joblib

        out["score"] = joblib.load(cal_path).predict(out["score"].to_numpy())
    return out


def assign_priority(ranked: pd.DataFrame, op: dict[str, Any]) -> pd.Series:
    k = int(op["primary_k"])
    thr = float(op["threshold"])
    pr = np.where(ranked["rank"] <= k, "high", np.where(ranked["score"] >= thr, "medium", "low"))
    return pd.Series(pr, index=ranked.index, name="review_priority")
