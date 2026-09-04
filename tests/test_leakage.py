"""FR-043: split disjointness, monotone time ranges, and train-only fitting of every transform."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aml_triage.config import load
from aml_triage.data.split import MANIFEST_NAME, make_split, write_split
from aml_triage.features.base import load_registry
from aml_triage.features.pipeline import (
    FitScopeRecorder,
    LeakageError,
    assert_fit_scope,
    build_feature_matrices,
    load_feature_matrix,
    read_fitscope,
)
from aml_triage.features.transaction import AmountBucketizer


@pytest.fixture
def built(tmp_path: Path, repo_root: Path, fixture_frame):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "processed_dir": str(tmp_path / "processed"),
                    "raw_csv": str(tmp_path / "f.csv"),
                },
                "split": {"train_end_step": 40, "val_end_step": 56, "min_positives_per_split": 1},
                "review": {"review_period_steps": 24, "primary_k": 5, "k_grid": [5, 10]},
            }
        )
    )
    cfg = load(cfg_path)
    parts, manifest = make_split(fixture_frame, cfg)
    write_split(parts, manifest, cfg.paths.processed_dir)
    for s in ("primary", "strict_pretx", "posttx_ablation"):
        build_feature_matrices(cfg, s)
    return cfg


def test_splits_disjoint_and_monotone(built) -> None:
    m = json.loads((Path(built.paths.processed_dir) / MANIFEST_NAME).read_text())
    r = m["step_ranges"]
    assert r["train"][1] < r["val"][0] <= r["val"][1] < r["test"][0]
    idx = {
        s: set(load_feature_matrix(built.paths.processed_dir, "primary", s)[1]["row_index"])
        for s in ("train", "val", "test")
    }
    assert (
        not (idx["train"] & idx["val"])
        and not (idx["train"] & idx["test"])
        and not (idx["val"] & idx["test"])
    )


def test_transforms_fitted_only_on_train(built) -> None:
    for s in ("primary", "strict_pretx", "posttx_ablation"):
        rec = read_fitscope(built.paths.processed_dir, s)
        assert rec["fitted_on"] == ["train"]
        assert sorted(rec["transformed_on"]) == ["test", "train", "val"]
        assert_fit_scope(rec)


def test_strict_pretx_has_no_batch_only_columns(built) -> None:
    batch_only = {d.name for d in load_registry() if d.available_at_prediction_time == "batch_only"}
    X, _ = load_feature_matrix(built.paths.processed_dir, "strict_pretx", "train")
    assert not (batch_only & set(X.columns))
    X_primary, _ = load_feature_matrix(built.paths.processed_dir, "primary", "train")
    assert batch_only <= set(X_primary.columns)


def test_no_identifier_or_label_columns_in_X(built) -> None:
    X, meta = load_feature_matrix(built.paths.processed_dir, "primary", "test")
    assert not ({"nameOrig", "nameDest", "isFraud", "isFlaggedFraud"} & set(X.columns))
    assert {"row_index", "step", "isFraud", "isFlaggedFraud", "type"} <= set(meta.columns)


def test_val_and_test_transformed_with_train_edges(built) -> None:
    import joblib

    ct = joblib.load(Path(built.paths.processed_dir) / "feature_pipeline_primary.joblib")
    bucket = ct.named_transformers_["amount_bucket"]
    train_amounts = pd.read_parquet(Path(built.paths.processed_dir) / "train.parquet")[
        "amount"
    ].to_numpy()
    expected = AmountBucketizer(n_bins=10).fit(train_amounts.reshape(-1, 1)).edges_
    assert (bucket.edges_ == expected).all()


def test_deliberate_leak_is_detected() -> None:
    rec = FitScopeRecorder(AmountBucketizer())
    rec.fit([[1.0], [2.0], [3.0]], split_id="test")
    with pytest.raises(LeakageError):
        assert_fit_scope(rec.record())
    with pytest.raises(LeakageError):
        assert_fit_scope({"fitted_on": []})


def test_resampled_rows_only_in_train_placeholder() -> None:
    """Resampling is introduced in Milestone 5; the guard contract is: any sampler lives inside the
    estimator pipeline's ``fit`` and never touches validation or test rows. Enforced by the fit-scope
    record: ``fitted_on`` must be exactly ['train']."""
    assert_fit_scope({"fitted_on": ["train"], "transformed_on": ["train", "val", "test"]})
