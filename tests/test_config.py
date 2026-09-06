from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aml_triage.cli import main
from aml_triage.config import Config, load
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_VALIDATION
from aml_triage.evaluation.threshold import guard_operating_point_path


def test_load_base_config(base_config_path: Path) -> None:
    cfg = load(base_config_path)
    assert isinstance(cfg, Config)
    assert cfg.seed == 42
    assert cfg.split.strategy == "temporal"
    assert cfg.fairness.label == "operational error-slice analysis"
    assert cfg.source_path == base_config_path


def test_profiling_dependent_keys_are_set_from_profiling(base_config_path: Path) -> None:
    """V4, V8, V9 and V10 were resolved in task T025 from reports/data_quality.json."""
    cfg = load(base_config_path)
    assert cfg.split.train_end_step == 408 and cfg.split.val_end_step == 552
    assert cfg.split.min_positives_per_split == 500
    assert cfg.review.review_period_steps == 24 and cfg.review.primary_k == 200
    assert cfg.review.primary_k in cfg.review.k_grid
    assert cfg.tuning.tune_sample_rows == 1_000_000


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "not_a_real_section": {"x": 1}}))
    with pytest.raises(ValidationError):
        load(p)


def test_require_exits_2_on_null(tmp_path: Path) -> None:
    p = tmp_path / "null.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "review": {"primary_k": None}}))
    cfg = load(p)
    with pytest.raises(SystemExit) as exc:
        cfg.require(["review.primary_k"])
    assert exc.value.code == 2


def test_require_passes_when_set(tmp_path: Path) -> None:
    p = tmp_path / "ok.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "review": {"primary_k": 10, "k_grid": [10]}}))
    load(p).require(["review.primary_k"])


def test_missing_file_exits_2(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        load(tmp_path / "nope.yaml")
    assert exc.value.code == 2


def test_extends_deep_merges(tmp_path: Path) -> None:
    parent = tmp_path / "parent.yaml"
    child = tmp_path / "child.yaml"
    parent.write_text(yaml.safe_dump({"seed": 7, "compute": {"n_jobs": 8, "omp_num_threads": 8}}))
    child.write_text(yaml.safe_dump({"_extends": str(parent), "compute": {"n_jobs": 2}}))
    cfg = load(child)
    assert cfg.seed == 7
    assert cfg.compute.n_jobs == 2
    assert cfg.compute.omp_num_threads == 8


def test_smoke_config_extends_base(repo_root: Path) -> None:
    cfg = load(repo_root / "configs" / "smoke.yaml")
    assert cfg.seed == 42
    assert cfg.review.primary_k in cfg.review.k_grid
    assert cfg.paths.processed_dir.endswith("smoke")
    # The smoke run must never write the tracked, sealed operating point (T065 finding)
    assert cfg.operating_point_path != "configs/operating_point.yaml"
    assert cfg.operating_point_path.startswith(cfg.paths.models_dir)
    guard_operating_point_path(cfg)  # does not raise


def test_isolated_config_may_not_write_tracked_operating_point(
    tmp_path: Path, repo_root: Path
) -> None:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {"processed_dir": str(tmp_path / "processed")},
            }
        )
    )
    cfg = load(cfg_path)
    with pytest.raises(ValueError, match="isolated configurations must set operating_point_path"):
        guard_operating_point_path(cfg)
    assert main(["choose-operating-point", "--config", str(cfg_path)]) == EXIT_VALIDATION
    assert main(["freeze", "--config", str(cfg_path)]) in (EXIT_VALIDATION, EXIT_MISSING_PREREQ)


def test_seed_override(base_config_path: Path) -> None:
    assert load(base_config_path, overrides={"seed": 5}).seed == 5


def test_split_order_validated(tmp_path: Path) -> None:
    p = tmp_path / "split.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "split": {"train_end_step": 50, "val_end_step": 40}}))
    with pytest.raises(ValidationError):
        load(p)


def test_primary_k_must_be_in_grid(tmp_path: Path) -> None:
    p = tmp_path / "k.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "review": {"primary_k": 5, "k_grid": [10, 20]}}))
    with pytest.raises(ValidationError):
        load(p)


def test_config_hash_is_stable_and_sensitive(base_config_path: Path) -> None:
    a = load(base_config_path).config_hash()
    b = load(base_config_path).config_hash()
    c = load(base_config_path, overrides={"seed": 43}).config_hash()
    assert a == b
    assert a != c
    assert a.startswith("sha256:")
