from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from aml_triage.cli import main
from aml_triage.config import load
from aml_triage.constants import EXIT_GUARD, EXIT_OK
from aml_triage.data.split import (
    MANIFEST_NAME,
    ROW_INDEX,
    SplitGuardError,
    SplitManifest,
    make_split,
    write_split,
)


def _cfg(tmp_path: Path, repo_root: Path, **split_overrides):
    cfg = tmp_path / "cfg.yaml"
    body = {
        "_extends": str(repo_root / "configs" / "base.yaml"),
        "paths": {
            "processed_dir": str(tmp_path / "processed"),
            "raw_csv": str(tmp_path / "fixture.csv"),
        },
        "split": {
            "train_end_step": 40,
            "val_end_step": 56,
            "min_positives_per_split": 1,
            **split_overrides,
        },
        "review": {"review_period_steps": 24, "primary_k": 5, "k_grid": [5, 10]},
    }
    cfg.write_text(yaml.safe_dump(body))
    return cfg


def test_temporal_split_is_monotone_and_disjoint(
    tmp_path: Path, repo_root: Path, fixture_frame
) -> None:
    cfg = load(_cfg(tmp_path, repo_root))
    parts, manifest = make_split(fixture_frame, cfg)
    r = manifest.step_ranges
    assert r["train"][1] < r["val"][0] <= r["val"][1] < r["test"][0]
    idx = {k: set(v[ROW_INDEX]) for k, v in parts.items()}
    assert (
        not (idx["train"] & idx["val"])
        and not (idx["train"] & idx["test"])
        and not (idx["val"] & idx["test"])
    )
    assert sum(manifest.rows.values()) == len(fixture_frame)
    assert manifest.excluded_rows == {}
    assert manifest.config_hash.startswith("sha256:")
    assert manifest.frozen_at is None


def test_min_positives_guard(tmp_path: Path, repo_root: Path, fixture_frame) -> None:
    cfg = load(_cfg(tmp_path, repo_root, min_positives_per_split=10_000))
    with pytest.raises(SplitGuardError, match="min_positives_per_split"):
        make_split(fixture_frame, cfg)


def test_stratified_fallback_requires_and_records_reason(
    tmp_path: Path, repo_root: Path, fixture_frame
) -> None:
    cfg = load(
        _cfg(
            tmp_path,
            repo_root,
            strategy="stratified_fallback",
            fallback_reason="no positives in late steps (test)",
        )
    )
    parts, manifest = make_split(fixture_frame, cfg)
    assert manifest.strategy == "stratified_fallback"
    assert manifest.fallback_reason
    assert any("aggregate features MUST be excluded" in n for n in manifest.notes)
    assert sum(manifest.rows.values()) == len(fixture_frame)


def test_write_and_reread_manifest(tmp_path: Path, repo_root: Path, fixture_frame) -> None:
    cfg = load(_cfg(tmp_path, repo_root))
    parts, manifest = make_split(fixture_frame, cfg)
    path = write_split(parts, manifest, cfg.paths.processed_dir)
    back = SplitManifest.read(path)
    assert back.rows == manifest.rows
    assert (Path(cfg.paths.processed_dir) / "test.parquet").exists()


def test_frozen_manifest_refuses_resplit(tmp_path: Path, repo_root: Path, fixture_frame) -> None:
    cfg = load(_cfg(tmp_path, repo_root))
    parts, manifest = make_split(fixture_frame, cfg)
    path = write_split(parts, manifest, cfg.paths.processed_dir)
    data = json.loads(path.read_text())
    data["frozen_at"] = "2026-09-05T00:00:00+00:00"
    path.write_text(json.dumps(data))
    frozen_text = path.read_text()
    # Identical partition (a clean clone replaying the pipeline): parquet files regenerate, manifest untouched
    (Path(cfg.paths.processed_dir) / "test.parquet").unlink()
    write_split(parts, manifest, cfg.paths.processed_dir)
    assert (Path(cfg.paths.processed_dir) / "test.parquet").exists()
    assert path.read_text() == frozen_text
    # Different partition: refused
    other = replace(manifest, rows={**manifest.rows, "train": manifest.rows["train"] - 1})
    with pytest.raises(SplitGuardError, match="frozen"):
        write_split(parts, other, cfg.paths.processed_dir)


def test_cli_split_end_to_end_and_guard_exit_code(
    tmp_path: Path, repo_root: Path, fixture_frame
) -> None:
    fixture_frame.to_csv(tmp_path / "fixture.csv", index=False)
    cfg = _cfg(tmp_path, repo_root)
    assert main(["split", "--config", str(cfg)]) == EXIT_OK
    manifest = json.loads((tmp_path / "processed" / MANIFEST_NAME).read_text())
    assert manifest["strategy"] == "temporal"
    bad = _cfg(tmp_path, repo_root, min_positives_per_split=10_000)
    assert main(["split", "--config", str(bad)]) == EXIT_GUARD
