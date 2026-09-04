from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aml_triage.cli import main
from aml_triage.config import load
from aml_triage.constants import EXIT_GUARD, EXIT_OK
from aml_triage.data.split import make_split, write_split
from aml_triage.features.pipeline import build_feature_matrices
from aml_triage.models.train import TestAccessError, assert_split_allowed, train_and_score


@pytest.fixture
def m5_cfg(tmp_path: Path, repo_root: Path, fixture_frame):
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
            }
        )
    )
    cfg = load(cfg_path)
    parts, manifest = make_split(fixture_frame, cfg)
    write_split(parts, manifest, cfg.paths.processed_dir)
    build_feature_matrices(cfg, "primary")
    return cfg, cfg_path


def test_train_dummy_and_logreg_on_fixture(m5_cfg) -> None:
    cfg, _ = m5_cfg
    dummy = train_and_score(cfg, "dummy", "primary", "val")
    assert dummy["metrics"]["degenerate_scores"] is True
    assert dummy["fit_scope"]["fitted_on"] == ["train"] and dummy["fit_scope"][
        "transformed_on"
    ] == ["val"]
    lr = train_and_score(cfg, "logreg", "primary", "val")
    assert lr["metrics"]["degenerate_scores"] is False
    assert set(lr["recall_at_k"]) == {"5", "10"}
    run_dir = Path(cfg.paths.models_dir) / "runs" / "logreg__primary"
    assert (run_dir / "val_metrics.json").exists() and (
        run_dir / "val_predictions.parquet"
    ).exists()
    assert json.loads((run_dir / "val_metrics.json").read_text())["split"] == "val"


def test_test_split_is_locked_before_freeze(m5_cfg) -> None:
    cfg, cfg_path = m5_cfg
    with pytest.raises(TestAccessError, match="locked"):
        assert_split_allowed(cfg, "test", "train")
    assert (
        main(["train", "--config", str(cfg_path), "--models", "dummy", "--split", "test"])
        == EXIT_GUARD
    )


def test_train_never_scores_test_even_when_frozen(m5_cfg) -> None:
    cfg, _ = m5_cfg
    (Path(cfg.paths.processed_dir) / "test_access.json").write_text(json.dumps({"state": "frozen"}))
    with pytest.raises(TestAccessError, match="evaluate"):
        assert_split_allowed(cfg, "test", "train")
    assert_split_allowed(cfg, "test", "evaluate")  # allowed only through evaluate


def test_compare_cli_writes_report_with_comparators(m5_cfg) -> None:
    cfg, cfg_path = m5_cfg
    assert (
        main(["train", "--config", str(cfg_path), "--models", "dummy,logreg", "--split", "val"])
        == EXIT_OK
    )
    assert main(["compare", "--config", str(cfg_path), "--split", "val"]) == EXIT_OK
    text = (Path(cfg.paths.reports_dir) / "model_comparison.md").read_text()
    for needle in [
        "random ranking",
        "rule comparator",
        "dummy (chronological order)",
        "logreg [primary]",
        "Recall@5",
        "Recall@10",
        "majority-class accuracy",
    ]:
        assert needle in text, needle
    summary = json.loads((Path(cfg.paths.reports_dir) / "model_comparison_val.json").read_text())
    assert {"random_rank", "rule_rank", "dummy__primary", "logreg__primary"} <= set(summary["runs"])
