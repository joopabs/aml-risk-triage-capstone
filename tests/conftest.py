"""Shared fixtures. The synthetic frame mimics the expected PaySim schema but contains no PaySim rows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from aml_triage.utils.synthetic import EXPECTED_COLUMNS, TYPES, make_synthetic_frame  # noqa: E402

__all__ = ["EXPECTED_COLUMNS", "TYPES", "make_fixture_frame"]


def make_fixture_frame(
    seed: int = 0, n_rows: int = 600, n_steps: int = 72, n_positives: int = 12
) -> pd.DataFrame:
    """Small synthetic frame with planted defects (3 duplicates, 1 inconsistent balance)."""
    return make_synthetic_frame(
        seed=seed, n_rows=n_rows, n_steps=n_steps, n_positives=n_positives, plant_defects=True
    )


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def base_config_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "base.yaml"


@pytest.fixture
def fixture_frame() -> pd.DataFrame:
    return make_fixture_frame()


@pytest.fixture(scope="session")
def api_bundle(tmp_path_factory) -> Path:
    """Released bundle trained on synthetic rows through the real lifecycle (optional API + UI tests).

    Lives here (not in tests/api/conftest.py) because pytest scopes a conftest to its own directory
    and tests/ui needs the same bundle. Skips when FastAPI is not installed.
    """
    pytest.importorskip("fastapi")
    import os
    import shutil

    import yaml

    from aml_triage.cli import main
    from aml_triage.constants import EXIT_OK

    tmp = tmp_path_factory.mktemp("api_bundle")
    (tmp / "configs" / "models").mkdir(parents=True)
    for f in (REPO_ROOT / "configs" / "models").glob("*.yaml"):
        if ".tuned" not in f.name:
            shutil.copy(f, tmp / "configs" / "models" / f.name)
    shutil.copy(REPO_ROOT / "configs" / "schema.yaml", tmp / "configs" / "schema.yaml")
    reg = tmp / "features.yaml"
    shutil.copy(REPO_ROOT / "configs" / "features.yaml", reg)
    raw = tmp / "sample.csv"
    make_synthetic_frame(
        seed=3, n_rows=4000, n_steps=72, n_positives=80, plant_defects=False
    ).to_csv(raw, index=False)
    cfg = tmp / "cfg.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "_extends": str(REPO_ROOT / "configs" / "base.yaml"),
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
