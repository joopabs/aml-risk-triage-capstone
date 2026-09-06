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


# ---- Milestone 6: test-access state machine (locked -> frozen -> evaluated) ----
import json as _json  # noqa: E402

from aml_triage.cli import main as _main  # noqa: E402
from aml_triage.constants import EXIT_GUARD, EXIT_MISSING_PREREQ, EXIT_OK  # noqa: E402


@pytest.fixture
def m6(tmp_path: Path, repo_root: Path, fixture_frame):
    import shutil

    models_dir = tmp_path / "models_cfg"
    models_dir.mkdir()
    for f in (repo_root / "configs" / "models").glob("*.yaml"):
        if ".tuned" not in f.name:
            shutil.copy(f, models_dir / f.name)
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "processed_dir": str(tmp_path / "processed"),
                    "reports_dir": str(tmp_path / "reports"),
                    "models_dir": str(tmp_path / "models"),
                    "raw_csv": str(tmp_path / "f.csv"),
                },
                "split": {"train_end_step": 40, "val_end_step": 56, "min_positives_per_split": 1},
                "review": {"review_period_steps": 24, "primary_k": 5, "k_grid": [5, 10]},
                "operating_point_path": str(tmp_path / "operating_point.yaml"),
                "bootstrap": {"n_resamples": 5},
            }
        )
    )
    cfg = load(cfg_path)
    parts, manifest = make_split(fixture_frame, cfg)
    write_split(parts, manifest, cfg.paths.processed_dir)
    build_feature_matrices(cfg, "primary")
    assert (
        _main(
            [
                "train",
                "--config",
                str(cfg_path),
                "--models",
                "dummy,logreg",
                "--feature-set",
                "primary",
                "--split",
                "val",
            ]
        )
        == EXIT_OK
    )
    return cfg, cfg_path


def test_evaluate_locked_and_freeze_requires_operating_point(m6) -> None:
    cfg, cfg_path = m6
    assert _main(["evaluate", "--config", str(cfg_path), "--split", "test"]) == EXIT_GUARD
    assert (
        _main(["freeze", "--config", str(cfg_path)]) == EXIT_MISSING_PREREQ
    )  # no operating point yet
    assert _main(["select", "--config", str(cfg_path)]) == EXIT_MISSING_PREREQ


def test_single_touch_test_evaluation(m6) -> None:
    cfg, cfg_path = m6
    assert _main(["choose-operating-point", "--config", str(cfg_path)]) == EXIT_OK
    op = yaml.safe_load(Path(cfg.operating_point_path).read_text())
    assert (
        op["chosen_on"] == "val"
        and op["selected_run"] == "logreg__primary"
        and op["frozen_at"] is None
    )
    assert set(op["priority_rule"]) == {"high", "medium", "low"} and "k_score_cutoff" in op
    assert _main(["freeze", "--config", str(cfg_path)]) == EXIT_OK
    state = _json.loads((Path(cfg.paths.processed_dir) / "test_access.json").read_text())
    assert state["state"] == "frozen" and state["first_evaluated_at"] is None
    assert (
        _main(["freeze", "--config", str(cfg_path)]) == EXIT_OK
    )  # re-freeze before any test access is allowed and audited
    assert (
        len(
            _json.loads((Path(cfg.paths.processed_dir) / "test_access.json").read_text())[
                "refreezes"
            ]
        )
        == 1
    )
    assert (
        _main(["train", "--config", str(cfg_path), "--models", "dummy", "--split", "test"])
        == EXIT_GUARD
    )  # only evaluate may touch test
    assert _main(["evaluate", "--config", str(cfg_path), "--split", "test"]) == EXIT_OK
    state = _json.loads((Path(cfg.paths.processed_dir) / "test_access.json").read_text())
    assert (
        state["state"] == "evaluated"
        and state["first_evaluated_at"]
        and state["reevaluations"] == []
    )
    assert (
        _main(["evaluate", "--config", str(cfg_path), "--split", "test"]) == EXIT_GUARD
    )  # second touch refused
    assert (
        _main(["evaluate", "--config", str(cfg_path), "--split", "test", "--force-reevaluate"])
        == EXIT_GUARD
    )  # reason required
    assert (
        _main(
            [
                "evaluate",
                "--config",
                str(cfg_path),
                "--split",
                "test",
                "--force-reevaluate",
                "--reason",
                "unit test of the audit trail",
            ]
        )
        == EXIT_OK
    )
    state = _json.loads((Path(cfg.paths.processed_dir) / "test_access.json").read_text())
    assert state["reevaluations"][0]["reason"] == "unit test of the audit trail"
    # After test access, `freeze` is a no-op for the identical sealed operating point (so a clean
    # clone can replay `make pipeline`) and refuses anything different.
    access_path = Path(cfg.paths.processed_dir) / "test_access.json"
    before = access_path.read_bytes()
    op_path = Path(cfg.operating_point_path)
    op_text = op_path.read_text()
    assert _main(["choose-operating-point", "--config", str(cfg_path)]) == EXIT_OK
    assert op_path.read_text() == op_text  # identical replay keeps the sealed file byte-for-byte
    assert _main(["freeze", "--config", str(cfg_path)]) == EXIT_OK
    assert access_path.read_bytes() == before  # nothing rewritten
    assert yaml.safe_load(op_path.read_text())["frozen_at"]  # still sealed, so `select` can run
    op_path.write_text(op_text.replace("primary_k:", "primary_k: 7\n_tampered:"))
    assert (
        _main(["freeze", "--config", str(cfg_path)]) == EXIT_GUARD
    )  # never re-freeze a different operating point after the test split was evaluated
    op_path.write_text(op_text)
    test_metrics = _json.loads(
        (Path(cfg.paths.models_dir) / "runs" / "logreg__primary" / "test_metrics.json").read_text()
    )
    assert "bootstrap_ci" in test_metrics and test_metrics["split"] == "test"
    assert "operating_point_metrics" in test_metrics
    # select persists a bundle and LATEST; queue writes only permitted columns
    assert _main(["select", "--config", str(cfg_path)]) == EXIT_OK
    version = (Path(cfg.paths.models_dir) / "LATEST").read_text().strip()
    bundle = Path(cfg.paths.models_dir) / version
    for f in [
        "pipeline.joblib",
        "pipeline.sha256",
        "config_snapshot.yaml",
        "metrics.json",
        "feature_list.json",
        "model_card.md",
        "features.yaml",
    ]:
        assert (bundle / f).exists(), f
    assert _main(["queue", "--config", str(cfg_path), "--period", "0"]) == EXIT_OK
    q = (Path(cfg.paths.reports_dir) / "review_queue_period_0.md").read_text()
    header = [h.strip() for h in q.split("## Queue")[1].splitlines()[2].strip("|").split("|")]
    assert header == [
        "rank",
        "row_index",
        "step",
        "type",
        "risk_score",
        "review_priority",
        "model_version",
    ]
    assert "isFraud" not in q and "high" in q
    matrix = _json.loads((Path(cfg.paths.reports_dir) / "selection_matrix.json").read_text())
    assert sum(1 for r in matrix["rows"] if r["verdict"] == "selected") == 1


def test_reproduce_check_is_exact_on_fixture(m6) -> None:
    cfg, cfg_path = m6
    assert _main(["choose-operating-point", "--config", str(cfg_path)]) == EXIT_OK
    from aml_triage.models.lifecycle import reproduce_check

    out = reproduce_check(cfg)
    assert out["exact"] is True and out["tolerance"] == 0.0
    assert (Path(cfg.paths.reports_dir) / "reproducibility.json").exists()
