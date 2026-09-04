"""Feature registry loader and validation (configs/features.yaml)."""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

KNOWN_SETS = {"primary", "strict_pretx", "posttx_ablation", "selected", "pca_variant"}
KINDS = {"numeric", "categorical", "flag", "aggregate"}
AVAILABILITY = {"realtime", "batch_only"}
IDENTIFIER_COLUMNS = {"nameOrig", "nameDest"}


class RegistryError(ValueError):
    """Invalid feature registry. Exit code 2 at the CLI."""


@dataclass
class FeatureDef:
    name: str
    source_columns: list[str]
    transform: str
    rationale: str
    available_at_prediction_time: str
    kind: str
    sets: list[str] = field(default_factory=list)
    dictionary_entry: dict[str, Any] = field(default_factory=dict)

    @property
    def is_fitted(self) -> bool:
        return inspect.isclass(resolve(self.transform))

    @property
    def is_aggregate(self) -> bool:
        return self.kind == "aggregate"


def resolve(dotted: str) -> Any:
    module, _, attr = dotted.rpartition(".")
    return getattr(importlib.import_module(module), attr)


def load_registry(path: str | Path = "configs/features.yaml") -> list[FeatureDef]:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or []
    defs = [FeatureDef(**e) for e in raw]
    validate_registry(defs)
    return defs


def validate_registry(defs: list[FeatureDef]) -> None:
    names = [d.name for d in defs]
    if len(names) != len(set(names)):
        raise RegistryError("duplicate feature names")
    for d in defs:
        if not d.rationale.strip():
            raise RegistryError(f"{d.name}: rationale is required (FR-031)")
        if not d.dictionary_entry:
            raise RegistryError(f"{d.name}: dictionary_entry is required (FR-023)")
        if d.kind not in KINDS:
            raise RegistryError(f"{d.name}: unknown kind {d.kind!r}")
        if d.available_at_prediction_time not in AVAILABILITY:
            raise RegistryError(
                f"{d.name}: unknown availability {d.available_at_prediction_time!r}"
            )
        unknown = set(d.sets) - KNOWN_SETS
        if unknown:
            raise RegistryError(f"{d.name}: unknown sets {sorted(unknown)}")
        if "strict_pretx" in d.sets and d.available_at_prediction_time == "batch_only":
            raise RegistryError(f"{d.name}: strict_pretx may not contain batch_only features")
        try:
            resolve(d.transform)
        except (ImportError, AttributeError) as exc:
            raise RegistryError(
                f"{d.name}: transform {d.transform!r} not importable: {exc}"
            ) from exc


def features_for_set(defs: list[FeatureDef], set_name: str) -> list[FeatureDef]:
    if set_name not in KNOWN_SETS:
        raise RegistryError(f"unknown feature set {set_name!r}")
    chosen = [d for d in defs if set_name in d.sets]
    if not chosen:
        raise RegistryError(f"feature set {set_name!r} is empty (filled in a later milestone?)")
    return chosen


def compute_stateless(df: pd.DataFrame, defs: list[FeatureDef]) -> pd.DataFrame:
    """Apply every function-based, non-aggregate transform; returns one column per feature."""
    out: dict[str, pd.Series] = {}
    for d in defs:
        if d.is_aggregate or d.is_fitted:
            continue
        fn = resolve(d.transform)
        out[d.name] = fn(df).rename(d.name)
    return pd.DataFrame(out, index=df.index)


def model_columns(defs: list[FeatureDef]) -> list[str]:
    """Names of engineered columns that pass straight through to the model (not fitted/categorical)."""
    return [d.name for d in defs if not d.is_fitted and d.kind != "categorical"]
