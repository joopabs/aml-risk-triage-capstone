"""Train a candidate on the training split of a feature set and score another split (spec FR-051/053).

Runs are stored under ``models/runs/<model_id>__<feature_set>/`` with predictions, metrics, the fitted
estimator (gitignored), and a fit-scope record proving the estimator only saw training rows.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from aml_triage.config import Config
from aml_triage.constants import DISCLAIMER
from aml_triage.data.split import MANIFEST_NAME, SplitManifest
from aml_triage.evaluation.capacity import capacity_suite
from aml_triage.evaluation.metrics import compute_metrics
from aml_triage.features.pipeline import FitScopeRecorder, assert_fit_scope, load_feature_matrix
from aml_triage.models.registry import build, load_spec
from aml_triage.utils.io import ensure_dir, save_joblib, write_json, write_parquet

TEST_ACCESS = "test_access.json"
META_KEEP = ["row_index", "step", "isFraud", "isFlaggedFraud", "type"]


class TestAccessError(RuntimeError):
    """The test split may only be scored once the operating point is frozen (exit code 3)."""


def run_id(model_id: str, feature_set: str) -> str:
    return f"{model_id}__{feature_set}"


def runs_dir(cfg: Config) -> Path:
    return Path(cfg.paths.models_dir) / "runs"


def test_access_state(processed_dir: str | Path) -> dict[str, Any]:
    p = Path(processed_dir) / TEST_ACCESS
    if not p.exists():
        return {"state": "locked"}
    return json.loads(p.read_text(encoding="utf-8"))


def assert_split_allowed(cfg: Config, split: str, context: str) -> None:
    if split != "test":
        return
    state = test_access_state(cfg.paths.processed_dir).get("state", "locked")
    if state == "locked":
        raise TestAccessError(f"test split is locked for `{context}`; run `choose-operating-point` then `freeze` first")
    if context != "evaluate":
        raise TestAccessError(f"test split may only be scored through `evaluate` (state={state})")


class _Scorer:
    """Wraps a fitted estimator so ``FitScopeRecorder`` can record fit/transform scope."""

    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y=None):
        self.estimator.fit(X, y)
        return self

    def transform(self, X):
        return self.estimator.predict_proba(X)[:, 1]


def train_and_score(cfg: Config, model_id: str, feature_set: str, score_split: str = "val", context: str = "train") -> dict[str, Any]:
    assert_split_allowed(cfg, score_split, context)
    processed = Path(cfg.paths.processed_dir)
    manifest = SplitManifest.read(processed / MANIFEST_NAME)
    spec = load_spec(model_id, cfg)
    X_train, meta_train = load_feature_matrix(processed, feature_set, "train")
    y_train = meta_train["isFraud"].astype(int)

    rec = FitScopeRecorder(_Scorer(build(model_id, cfg)))
    t0 = time.perf_counter()
    rec.fit(X_train, y_train, split_id="train")
    fit_seconds = time.perf_counter() - t0

    X_s, meta_s = load_feature_matrix(processed, feature_set, score_split)
    scores = rec.transform(X_s, split_id=score_split)
    assert_fit_scope(rec.record())

    preds = meta_s[META_KEEP].copy()
    preds["score"] = scores
    metrics = compute_metrics(preds["isFraud"], preds["score"], threshold=0.5, degenerate_eps=cfg.evaluation.degenerate_eps)
    capacity = capacity_suite(preds[["row_index", "step", "isFraud", "score"]], cfg.review.k_grid, cfg.review.review_period_steps)

    out_dir = ensure_dir(runs_dir(cfg) / run_id(model_id, feature_set))
    write_parquet(preds, out_dir / f"{score_split}_predictions.parquet")
    save_joblib(rec.transformer.estimator, out_dir / f"model_{feature_set}.joblib")
    result = {
        "candidate_id": model_id,
        "feature_set": feature_set,
        "split": score_split,
        "description": spec.description,
        "imbalance_strategy": spec.imbalance_strategy,
        "tuned_params_used": spec.tuned,
        "params": {k: (v if isinstance(v, (int, float, str, bool)) or v is None else str(v)) for k, v in spec.params.items()},
        "n_train_rows": int(len(X_train)),
        "n_train_positives": int(y_train.sum()),
        "fit_seconds": round(fit_seconds, 2),
        "k_grid": list(cfg.review.k_grid),
        "primary_k": cfg.review.primary_k,
        "metrics": metrics,
        "recall_at_k": {k: v["recall_at_k"] for k, v in capacity.items()},
        "precision_at_k": {k: v["precision_at_k"] for k, v in capacity.items()},
        "per_period": capacity[str(cfg.review.primary_k)]["per_period"],
        "fit_scope": rec.record(),
        "split_manifest_hash": manifest.config_hash,
        "config_hash": cfg.config_hash(),
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
    }
    write_json(result, out_dir / f"{score_split}_metrics.json")
    return result


def load_run(cfg: Config, rid: str, split: str) -> tuple[dict[str, Any], pd.DataFrame]:
    d = runs_dir(cfg) / rid
    metrics = json.loads((d / f"{split}_metrics.json").read_text(encoding="utf-8"))
    preds = pd.read_parquet(d / f"{split}_predictions.parquet")
    return metrics, preds


def list_runs(cfg: Config, split: str) -> list[str]:
    d = runs_dir(cfg)
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if (p / f"{split}_metrics.json").exists())
