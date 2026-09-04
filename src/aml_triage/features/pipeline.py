"""Feature matrices per set, with every fitted transform fitted on training rows only (FR-042)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from aml_triage.config import Config
from aml_triage.data.split import MANIFEST_NAME, SPLITS, SplitManifest, load_split
from aml_triage.features.aggregates import causal_aggregates
from aml_triage.features.base import (
    FeatureDef,
    compute_stateless,
    features_for_set,
    load_registry,
    model_columns,
    resolve,
)
from aml_triage.utils.io import save_joblib, write_json, write_parquet

META_COLUMNS = ["row_index", "step", "isFraud", "isFlaggedFraud", "type"]
META_PREFIX = "meta_"


class LeakageError(RuntimeError):
    """A fitted transform saw rows outside the training split. Exit code 3."""


@dataclass
class FitScopeRecorder:
    """Wraps a transformer and records which split each fit/transform call used."""

    transformer: Any
    fitted_on: list[str] = field(default_factory=list)
    transformed_on: list[str] = field(default_factory=list)

    def fit(self, X, y=None, *, split_id: str):
        self.fitted_on.append(split_id)
        self.transformer.fit(X, y)
        return self

    def transform(self, X, *, split_id: str):
        self.transformed_on.append(split_id)
        return self.transformer.transform(X)

    def record(self) -> dict[str, Any]:
        return {"fitted_on": list(self.fitted_on), "transformed_on": list(self.transformed_on)}


def assert_fit_scope(record: dict[str, Any]) -> None:
    bad = [s for s in record.get("fitted_on", []) if s != "train"]
    if bad or not record.get("fitted_on"):
        raise LeakageError(
            f"fitted transforms must see only the training split; saw {record.get('fitted_on')}"
        )


def build_column_transformer(defs: list[FeatureDef]) -> ColumnTransformer:
    transformers = []
    for d in defs:
        if d.kind == "categorical":
            transformers.append(
                (
                    d.name,
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype="float32"),
                    d.source_columns,
                )
            )
        elif d.is_fitted:
            transformers.append((d.name, resolve(d.transform)(), d.source_columns))
    passthrough = model_columns(defs)
    if passthrough:
        transformers.append(("engineered", "passthrough", passthrough))
    ct = ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False)
    ct.set_output(transform="pandas")
    return ct


def engineer(
    frame: pd.DataFrame, defs: list[FeatureDef], allow_aggregates: bool = True
) -> pd.DataFrame:
    """Raw columns needed by fitted transforms + all stateless and aggregate engineered columns."""
    parts = [frame[["type", "amount"]]]
    stateless = compute_stateless(frame, defs)
    if not stateless.empty:
        parts.append(stateless)
    agg_names = [d.name for d in defs if d.is_aggregate]
    if agg_names and allow_aggregates:
        parts.append(causal_aggregates(frame, agg_names))
    return pd.concat(parts, axis=1)


def build_feature_matrices(
    cfg: Config, set_name: str, registry_path: str | Path | None = None
) -> dict[str, Path]:
    processed = Path(cfg.paths.processed_dir)
    manifest = SplitManifest.read(processed / MANIFEST_NAME)
    defs = features_for_set(load_registry(registry_path or cfg.features.registry), set_name)
    allow_aggregates = manifest.strategy == "temporal"
    if not allow_aggregates:
        defs = [d for d in defs if not d.is_aggregate]  # FR-041

    # Aggregates look strictly backward, so computing them over the whole ordered timeline is
    # causal: a validation row sees earlier training rows (past), never later rows.
    frames = {name: load_split(processed, name).assign(__split=name) for name in SPLITS}
    full = pd.concat(frames.values(), axis=0).sort_values(["step", "row_index"], kind="stable")
    engineered = engineer(full, defs, allow_aggregates=allow_aggregates)
    engineered["__split"] = full["__split"].to_numpy()
    meta = full[META_COLUMNS].add_prefix(META_PREFIX)

    recorder = FitScopeRecorder(build_column_transformer(defs))
    train_mask = engineered["__split"] == "train"
    recorder.fit(engineered.loc[train_mask].drop(columns="__split"), split_id="train")
    outputs: dict[str, Path] = {}
    for name in SPLITS:
        mask = engineered["__split"] == name
        X = recorder.transform(engineered.loc[mask].drop(columns="__split"), split_id=name)
        X = pd.concat([X.reset_index(drop=True), meta.loc[mask].reset_index(drop=True)], axis=1)
        outputs[name] = write_parquet(X, processed / f"features_{set_name}_{name}.parquet")
    assert_fit_scope(recorder.record())

    save_joblib(recorder.transformer, processed / f"feature_pipeline_{set_name}.joblib")
    write_json(recorder.record(), processed / f"feature_pipeline_{set_name}.fitscope.json")
    feature_names = [
        c for c in pd.read_parquet(outputs["train"]).columns if not c.startswith(META_PREFIX)
    ]
    write_json(
        {
            "set": set_name,
            "features": feature_names,
            "registry_features": [d.name for d in defs],
            "batch_only": [d.name for d in defs if d.available_at_prediction_time == "batch_only"],
            "aggregates_included": allow_aggregates and any(d.is_aggregate for d in defs),
            "config_hash": cfg.config_hash(),
        },
        processed / f"features_{set_name}.json",
    )
    return outputs


def load_feature_matrix(
    processed_dir: str | Path, set_name: str, split: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (X, meta) for a split; meta columns are the ``meta_`` prefixed ones."""
    df = pd.read_parquet(Path(processed_dir) / f"features_{set_name}_{split}.parquet")
    meta_cols = [c for c in df.columns if c.startswith(META_PREFIX)]
    return df.drop(columns=meta_cols), df[meta_cols].rename(columns=lambda c: c[len(META_PREFIX) :])


def read_fitscope(processed_dir: str | Path, set_name: str) -> dict[str, Any]:
    with open(
        Path(processed_dir) / f"feature_pipeline_{set_name}.fitscope.json", encoding="utf-8"
    ) as fh:
        return json.load(fh)
