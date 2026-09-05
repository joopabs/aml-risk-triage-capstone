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
