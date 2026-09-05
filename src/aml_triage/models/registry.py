"""Candidate model factory driven by configs/models/*.yaml (spec FR-050/051, research R-03).

Deep learning is deliberately absent (research R-03). XGBoost is a documented optional swap: set
``estimator: xgboost.XGBClassifier`` in a model YAML if the package is installed.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from aml_triage.config import Config

MODELS_DIR = Path("configs/models")
CANDIDATE_IDS = ("dummy", "logreg", "balanced_rf", "hgb")
LEARNER_IDS = ("logreg", "balanced_rf", "hgb")
COMPARATOR_IDS = ("random_rank", "rule_rank")


@dataclass
class ModelSpec:
    id: str
    estimator: str
    params: dict[str, Any]
    imbalance_strategy: str
    scale_inputs: bool
    feature_set: str
    description: str = ""
    search_space: dict[str, Any] = field(default_factory=dict)
    tuned: bool = False


def _substitute(value: Any, cfg: Config) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return {"seed": cfg.seed, "n_jobs": cfg.compute.n_jobs}[key]
    if isinstance(value, dict):
        return {k: _substitute(v, cfg) for k, v in value.items()}
    return value


def tuned_path(model_id: str, cfg: Config, models_dir: str | Path = MODELS_DIR) -> Path:
    """Where tuned parameters live for this configuration.

    The base run (``paths.models_dir == "models"``) keeps the documented location
    ``configs/models/<id>.tuned.yaml``. Any other configuration (CI smoke, tests, experiments)
    writes under its own ``<models_dir>/tuning/`` so it can never overwrite the real search results.
    """
    if Path(cfg.paths.models_dir).as_posix() == "models":
        return Path(models_dir) / f"{model_id}.tuned.yaml"
    return Path(cfg.paths.models_dir) / "tuning" / f"{model_id}.tuned.yaml"


def load_spec(model_id: str, cfg: Config, prefer_tuned: bool = True, models_dir: str | Path = MODELS_DIR) -> ModelSpec:
    base = Path(models_dir) / f"{model_id}.yaml"
    if not base.exists():
        raise FileNotFoundError(f"unknown model id {model_id!r}: {base} not found")
    raw = yaml.safe_load(base.read_text(encoding="utf-8"))
    tuned_path_ = tuned_path(model_id, cfg, models_dir)
    tuned = False
    if prefer_tuned and tuned_path_.exists():
        tuned_raw = yaml.safe_load(tuned_path_.read_text(encoding="utf-8")) or {}
        raw["params"] = {**raw.get("params", {}), **tuned_raw.get("params", {})}
        tuned = True
    params = _substitute(raw.get("params", {}), cfg)
    return ModelSpec(
        id=raw["id"],
        estimator=raw["estimator"],
        params=params,
        imbalance_strategy=raw.get("imbalance_strategy", "none"),
        scale_inputs=bool(raw.get("scale_inputs", False)),
        feature_set=raw.get("feature_set", cfg.features.default_set),
        description=raw.get("description", ""),
        search_space=raw.get("search_space", {}) or {},
        tuned=tuned,
    )


def instantiate(spec: ModelSpec, params_override: dict[str, Any] | None = None):
    module, _, cls_name = spec.estimator.rpartition(".")
    cls = getattr(importlib.import_module(module), cls_name)
    est = cls(**{**spec.params, **(params_override or {})})
    if spec.scale_inputs:
        return Pipeline([("scale", StandardScaler()), ("model", est)])
    return est


def build(model_id: str, cfg: Config, params_override: dict[str, Any] | None = None, prefer_tuned: bool = True):
    return instantiate(load_spec(model_id, cfg, prefer_tuned=prefer_tuned), params_override)


def estimator_param_prefix(spec: ModelSpec) -> str:
    """Prefix for search-space keys when the estimator is wrapped in a scaling pipeline."""
    return "model__" if spec.scale_inputs else ""
