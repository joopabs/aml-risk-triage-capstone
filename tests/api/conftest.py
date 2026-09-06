"""Fixture bundle for the API tests: trained on synthetic rows, released through the real lifecycle."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

pytest.importorskip("fastapi")

from aml_triage.cli import main  # noqa: E402
from aml_triage.constants import EXIT_OK  # noqa: E402
from aml_triage.utils.synthetic import make_synthetic_frame  # noqa: E402


@pytest.fixture(scope="session")
def api_bundle(tmp_path_factory) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    tmp = tmp_path_factory.mktemp("api_bundle")
    (tmp / "configs" / "models").mkdir(parents=True)
    for f in (repo_root / "configs" / "models").glob("*.yaml"):
        if ".tuned" not in f.name:
            shutil.copy(f, tmp / "configs" / "models" / f.name)
    shutil.copy(repo_root / "configs" / "schema.yaml", tmp / "configs" / "schema.yaml")
    reg = tmp / "features.yaml"
    shutil.copy(repo_root / "configs" / "features.yaml", reg)
    raw = tmp / "sample.csv"
    make_synthetic_frame(
        seed=3, n_rows=4000, n_steps=72, n_positives=80, plant_defects=False
    ).to_csv(raw, index=False)
    cfg = tmp / "cfg.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "raw_csv": str(raw),
                    "processed_dir": str(tmp / "processed"),
                    "models_dir": str(tmp / "models"),
                    "reports_dir": str(tmp / "reports"),
                },
                "features": {"registry": str(reg)},
                "split": {"train_end_step": 48, "val_end_step": 60, "min_positives_per_split": 5},
                "review": {"review_period_steps": 24, "primary_k": 10, "k_grid": [5, 10, 20]},
                "bootstrap": {"n_resamples": 3},
                "operating_point_path": str(tmp / "operating_point.yaml"),
            }
        )
    )
    cwd = Path.cwd()
    import os

    os.chdir(tmp)
    try:
        for args in (
            ["split"],
            ["build-features", "--feature-set", "primary"],
            ["train", "--models", "dummy,hgb", "--feature-set", "primary", "--split", "val"],
            ["choose-operating-point"],
            ["freeze"],
            ["evaluate", "--split", "test"],
            ["select"],
        ):
            assert main([*args, "--config", str(cfg)]) == EXIT_OK, args
    finally:
        os.chdir(cwd)
    return tmp / "models"
