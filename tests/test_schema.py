from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aml_triage.data.load import load_raw, read_header
from aml_triage.data.schema import SchemaError, assert_valid, load_schema, validate_frame
from tests.conftest import EXPECTED_COLUMNS


@pytest.fixture(scope="module")
def schema():
    return load_schema()


def test_schema_matches_expected_columns(schema) -> None:
    assert schema.names == EXPECTED_COLUMNS
    assert schema.by_role("identifier") == ["nameOrig", "nameDest"]
    assert schema.by_role("target") == ["isFraud"]
    assert schema.by_role("rule_comparator") == ["isFlaggedFraud"]
    assert schema.by_role("time_index") == ["step"]


def test_fixture_frame_is_valid(fixture_frame, schema) -> None:
    report = validate_frame(fixture_frame, schema)
    assert report.ok, report.summary()
    assert report.n_rows == len(fixture_frame)
    assert report.unexpected_columns == []


def test_missing_column_fails(fixture_frame, schema) -> None:
    report = validate_frame(fixture_frame.drop(columns=["amount"]), schema)
    assert report.missing_columns == ["amount"]
    assert not report.ok
    with pytest.raises(SchemaError):
        assert_valid(fixture_frame.drop(columns=["amount"]), schema)


def test_non_numeric_value_fails(fixture_frame, schema) -> None:
    bad = fixture_frame.copy()
    bad["amount"] = bad["amount"].astype(object)
    bad.loc[3, "amount"] = "twelve"
    report = validate_frame(bad, schema)
    assert "amount" in report.dtype_problems
    assert not report.ok


def test_null_in_non_nullable_fails(fixture_frame, schema) -> None:
    bad = fixture_frame.copy()
    bad.loc[2, "step"] = pd.NA
    report = validate_frame(bad, schema)
    assert report.null_violations.get("step") == 1


def test_allowed_values_enforced(fixture_frame, schema) -> None:
    bad = fixture_frame.copy()
    bad.loc[4, "isFraud"] = 2
    report = validate_frame(bad, schema)
    assert report.allowed_violations == {"isFraud": 1}


def test_soft_min_is_counted_not_fatal(fixture_frame, schema) -> None:
    odd = fixture_frame.copy()
    odd.loc[6, "amount"] = -5.0
    report = validate_frame(odd, schema)
    assert report.soft_min_violations["amount"] == 1
    assert report.hard_min_violations == {}
    assert report.ok  # soft minimums are counted for profiling, never fatal


def test_load_raw_from_csv_roundtrip(tmp_path: Path, fixture_frame, schema) -> None:
    csv = tmp_path / "sample.csv"
    fixture_frame.to_csv(csv, index=False)
    assert read_header(csv) == EXPECTED_COLUMNS
    df = load_raw(csv, schema)
    assert len(df) == len(fixture_frame)
    assert str(df["amount"].dtype) == "float32"
    assert str(df["isFraud"].dtype) == "int8"
    assert str(df["type"].dtype) == "category"


def test_load_raw_missing_column_raises_before_read(tmp_path: Path, fixture_frame, schema) -> None:
    csv = tmp_path / "bad.csv"
    fixture_frame.drop(columns=["nameDest"]).to_csv(csv, index=False)
    with pytest.raises(SchemaError, match="nameDest"):
        load_raw(csv, schema)


def test_load_raw_missing_file(tmp_path: Path, schema) -> None:
    with pytest.raises(FileNotFoundError):
        load_raw(tmp_path / "nope.csv", schema)
