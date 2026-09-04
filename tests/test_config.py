from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aml_triage.config import Config, load


def test_load_base_config(base_config_path: Path) -> None:
    cfg = load(base_config_path)
    assert isinstance(cfg, Config)
    assert cfg.seed == 42
    assert cfg.split.strategy == "temporal"
    assert cfg.fairness.label == "operational error-slice analysis"
    assert cfg.source_path == base_config_path


def test_profiling_dependent_keys_are_null_in_base(base_config_path: Path) -> None:
    cfg = load(base_config_path)
    for key in [
        "paths.raw_csv",
        "split.train_end_step",
        "split.val_end_step",
        "split.min_positives_per_split",
        "review.review_period_steps",
        "review.primary_k",
        "tuning.tune_sample_rows",
    ]:
        assert cfg.get(key) is None, f"{key} must stay null until profiling records it"


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump({"seed": 1, "not_a_real_section": {"x": 1}}))
    with pytest.raises(ValidationError):
        load(p)


def test_require_exits_2_on_null(base_config_path: Path) -> None:
    cfg = load(base_config_path)
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
