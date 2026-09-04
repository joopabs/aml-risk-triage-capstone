from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from aml_triage.constants import DISCLAIMER, MODEL_OUTPUT_FIELDS, PROHIBITED_OUTPUT_FIELDS
from aml_triage.utils.io import (
    MODEL_VERSION_PATTERN,
    model_version,
    read_json,
    read_parquet,
    sha256_file,
    write_json,
    write_parquet,
)
from aml_triage.utils.logging import get_logger
from aml_triage.utils.seed import set_global_seed


def test_disclaimer_content() -> None:
    low = DISCLAIMER.lower()
    for word in ["synthetic", "educational", "human", "blocking", "account closure", "regulatory"]:
        assert word in low, f"disclaimer must mention {word!r}"
    assert "determination" in low


def test_output_field_lists_are_disjoint() -> None:
    assert not set(MODEL_OUTPUT_FIELDS) & set(PROHIBITED_OUTPUT_FIELDS)


def test_model_version_format() -> None:
    fixed = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    v = model_version("hgb", now=fixed, git_sha="abc1234")
    assert v == "20260904T120000-abc1234-hgb"
    assert MODEL_VERSION_PATTERN.match(v)
    assert re.match(r"^\d{8}T\d{6}-[0-9a-f]{7}-\w+$", model_version("logreg"))
    with pytest.raises(ValueError):
        model_version("bad id")


def test_set_global_seed_is_deterministic() -> None:
    a = set_global_seed(123).random(3)
    b = set_global_seed(123).random(3)
    assert np.allclose(a, b)
    assert np.random.rand() == pytest.approx(np.random.RandomState(123).rand())
    with pytest.raises(TypeError):
        set_global_seed("42")  # type: ignore[arg-type]


def test_json_and_parquet_roundtrip(tmp_path: Path, fixture_frame) -> None:
    j = write_json({"b": 1, "a": [1, 2]}, tmp_path / "x" / "y.json")
    assert read_json(j) == {"a": [1, 2], "b": 1}
    p = write_parquet(fixture_frame, tmp_path / "f.parquet")
    back = read_parquet(p)
    assert len(back) == len(fixture_frame)
    assert list(back.columns) == list(fixture_frame.columns)
    assert len(sha256_file(p)) == 64


def test_logger_is_idempotent() -> None:
    a = get_logger("aml_triage.test")
    b = get_logger("aml_triage.test")
    assert a is b and len(a.handlers) == 1
