"""Hyperparameter search on a seeded stratified training subsample (spec FR-052, research R-04).

Search: ``RandomizedSearchCV`` with ``average_precision`` and stratified folds inside the subsample.
The best parameters are written to ``configs/models/<id>.tuned.yaml`` and picked up automatically by
the registry; the full-train refit happens through ``train_and_score``.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.stats import loguniform, randint
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold

from aml_triage.config import Config
from aml_triage.features.pipeline import load_feature_matrix
from aml_triage.features.selection import stratified_subsample
from aml_triage.models.registry import MODELS_DIR, estimator_param_prefix, instantiate, load_spec
from aml_triage.utils.io import ensure_dir, write_json


def parse_search_space(space: dict[str, Any], prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, spec in space.items():
        key = f"{prefix}{name}"
        if "loguniform" in spec:
            lo, hi = spec["loguniform"]
            out[key] = loguniform(lo, hi)
        elif "randint" in spec:
            lo, hi = spec["randint"]
            out[key] = randint(lo, hi + 1)
        elif "choice" in spec:
            out[key] = list(spec["choice"])
        else:
            raise ValueError(f"unsupported search spec for {name}: {spec}")
    return out


def _jsonable(v: Any) -> Any:
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def tune_candidate(cfg: Config, model_id: str, feature_set: str | None = None, models_dir: str | Path = MODELS_DIR) -> dict[str, Any]:
    spec = load_spec(model_id, cfg, prefer_tuned=False, models_dir=models_dir)
    if not spec.search_space:
        raise ValueError(f"{model_id} has no search_space; nothing to tune")
    feature_set = feature_set or spec.feature_set
    X, meta = load_feature_matrix(cfg.paths.processed_dir, feature_set, "train")
    y = meta["isFraud"].astype(int)
    Xs, ys = stratified_subsample(X, y, cfg.tuning.tune_sample_rows or len(X), cfg.seed)

    prefix = estimator_param_prefix(spec)
    search = RandomizedSearchCV(
        instantiate(spec),
        parse_search_space(spec.search_space, prefix),
        n_iter=cfg.tuning.n_iter,
        scoring=cfg.tuning.scoring,
        cv=StratifiedKFold(n_splits=cfg.tuning.cv_folds, shuffle=True, random_state=cfg.seed),
        random_state=cfg.seed,
        n_jobs=cfg.compute.n_jobs,
        refit=False,
        error_score="raise",
    )
    t0 = time.perf_counter()
    search.fit(Xs, ys)
    seconds = time.perf_counter() - t0

    best = {k[len(prefix):] if prefix and k.startswith(prefix) else k: _jsonable(v) for k, v in search.best_params_.items()}
    tuned_path = Path(models_dir) / f"{model_id}.tuned.yaml"
    tuned_path.write_text(
        "# Written by `python -m aml_triage tune`; best RandomizedSearchCV params on a seeded training subsample.\n"
        + yaml.safe_dump(
            {
                "id": model_id,
                "params": best,
                "tuned_on": {
                    "feature_set": feature_set,
                    "subsample_rows": int(len(Xs)),
                    "subsample_positives": int(ys.sum()),
                    "n_iter": cfg.tuning.n_iter,
                    "cv_folds": cfg.tuning.cv_folds,
                    "scoring": cfg.tuning.scoring,
                    "best_cv_score": float(search.best_score_),
                    "seconds": round(seconds, 1),
                    "seed": cfg.seed,
                    "date": datetime.now(UTC).date().isoformat(),
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    cv = search.cv_results_
    log = {
        "model_id": model_id,
        "feature_set": feature_set,
        "best_params": best,
        "best_cv_score": float(search.best_score_),
        "seconds": round(seconds, 1),
        "trials": [
            {"params": {k: _jsonable(v) for k, v in p.items()}, "mean_score": float(m), "std_score": float(s), "rank": int(r)}
            for p, m, s, r in zip(cv["params"], cv["mean_test_score"], cv["std_test_score"], cv["rank_test_score"], strict=True)
        ],
        "config_hash": cfg.config_hash(),
    }
    write_json(log, ensure_dir(Path(cfg.paths.models_dir) / "tuning") / f"{model_id}_search.json")
    return log
