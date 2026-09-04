"""Typed, validated run configuration (contracts/config-schema.md).

Rules:
* Unknown keys are errors.
* Keys marked "set after Vn" in configs/base.yaml stay ``None`` until profiling records them;
  ``Config.require`` exits with code 2 when a command needs one that is still null.
* A YAML file may start with ``_extends: <path>``; the referenced file is loaded first and the
  current file's keys are deep-merged over it (used by configs/smoke.yaml).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from aml_triage.constants import EXIT_VALIDATION
from aml_triage.utils.io import sha256_text

_EXTENDS_KEY = "_extends"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PathsConfig(_Strict):
    raw_csv: str | None = None
    processed_dir: str = "data/processed"
    models_dir: str = "models"
    reports_dir: str = "reports"


class SplitConfig(_Strict):
    strategy: Literal["temporal", "stratified_fallback"] = "temporal"
    train_end_step: int | None = None
    val_end_step: int | None = None
    min_positives_per_split: int | None = None
    fallback_reason: str | None = None

    @model_validator(mode="after")
    def _ordered(self) -> SplitConfig:
        if self.train_end_step is not None and self.val_end_step is not None:
            if not self.train_end_step < self.val_end_step:
                raise ValueError("split.train_end_step must be < split.val_end_step")
        if self.strategy == "stratified_fallback" and not self.fallback_reason:
            raise ValueError(
                "split.fallback_reason is required when strategy is stratified_fallback"
            )
        return self


class ReviewConfig(_Strict):
    review_period_steps: int | None = Field(default=None, gt=0)
    primary_k: int | None = Field(default=None, gt=0)
    k_grid: list[int] = Field(default_factory=list)
    tie_break: list[str] = Field(
        default_factory=lambda: ["score_desc", "step_asc", "row_index_asc"]
    )

    @model_validator(mode="after")
    def _k_in_grid(self) -> ReviewConfig:
        if self.primary_k is not None and self.k_grid and self.primary_k not in self.k_grid:
            raise ValueError("review.primary_k must be a member of review.k_grid")
        return self


class FeaturesConfig(_Strict):
    registry: str = "configs/features.yaml"
    default_set: str = "primary"
    ablation_sets: list[str] = Field(default_factory=list)


class SelectionConfig(_Strict):
    mi_k: int | None = None
    l1_c: float | None = None
    combine_rule: str = "intersection_or_union_if_lt"
    min_size: int | None = None


class PcaConfig(_Strict):
    n_components: int | float | None = None
    role: str = "diagnostic_and_visualization"


class TuningConfig(_Strict):
    tune_sample_rows: int | None = None
    n_iter: int = 30
    cv_folds: int = 3
    scoring: str = "average_precision"


class CalibrationConfig(_Strict):
    method: Literal["none", "isotonic_val"] = "isotonic_val"
    max_pr_auc_drop: float = 0.005


class BootstrapConfig(_Strict):
    n_resamples: int = 200


class EvaluationConfig(_Strict):
    degenerate_eps: float = 1e-9


class ExplainConfig(_Strict):
    shap_background_rows: int = 1000
    shap_eval_rows: int = 2000
    n_local_examples: int = 3
    pdp_top_features: int = 5


class FairnessConfig(_Strict):
    slice_dimensions: list[str] = Field(default_factory=list)
    label: str = "operational error-slice analysis"


class ComputeConfig(_Strict):
    n_jobs: int = 4
    omp_num_threads: int = 4


class Config(_Strict):
    seed: int
    paths: PathsConfig = Field(default_factory=PathsConfig)
    split: SplitConfig = Field(default_factory=SplitConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    pca: PcaConfig = Field(default_factory=PcaConfig)
    tuning: TuningConfig = Field(default_factory=TuningConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    operating_point_path: str = "configs/operating_point.yaml"
    bootstrap: BootstrapConfig = Field(default_factory=BootstrapConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    explain: ExplainConfig = Field(default_factory=ExplainConfig)
    fairness: FairnessConfig = Field(default_factory=FairnessConfig)
    compute: ComputeConfig = Field(default_factory=ComputeConfig)
    disclaimer_ref: str = "aml_triage.constants.DISCLAIMER"

    _source_path: Path | None = PrivateAttr(default=None)
    _schema_path: Path = PrivateAttr(default=Path("configs/schema.yaml"))

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    def get(self, dotted: str) -> Any:
        """Return a nested value by dotted path, e.g. ``"review.primary_k"``."""
        node: Any = self
        for part in dotted.split("."):
            node = getattr(node, part) if isinstance(node, BaseModel) else node[part]
        return node

    def require(self, keys: list[str]) -> None:
        """Exit with code 2 if any of the dotted keys is still null."""
        missing = [k for k in keys if self.get(k) is None]
        if missing:
            src = self._source_path or "<config>"
            print(
                f"config error: {src}: the following keys are required for this command but are "
                f"null (fill them from profiling results): {', '.join(missing)}",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_VALIDATION)

    def config_hash(self) -> str:
        """sha256 over the effective config plus configs/schema.yaml (if present)."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        schema_text = self._schema_path.read_text() if self._schema_path.exists() else ""
        return "sha256:" + sha256_text(payload + "\n---\n" + schema_text)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml_chain(path: Path, seen: tuple[Path, ...] = ()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in seen:
        raise ValueError(f"circular _extends chain at {path}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    parent_ref = data.pop(_EXTENDS_KEY, None)
    if parent_ref is None:
        return data
    parent_path = Path(parent_ref)
    if not parent_path.is_absolute() and not parent_path.exists():
        parent_path = path.parent / parent_path
    parent = _read_yaml_chain(parent_path, seen + (resolved,))
    return _deep_merge(parent, data)


def load(path: str | Path, overrides: dict[str, Any] | None = None) -> Config:
    """Load, merge (``_extends``), apply overrides, and validate a config file."""
    p = Path(path)
    if not p.exists():
        print(f"config error: file not found: {p}", file=sys.stderr)
        raise SystemExit(EXIT_VALIDATION)
    data = _read_yaml_chain(p)
    if overrides:
        data = _deep_merge(data, overrides)
    try:
        cfg = Config.model_validate(data)
    except ValidationError as exc:
        print(f"config error: {p}:\n{exc}", file=sys.stderr)
        raise
    cfg._source_path = p
    return cfg
