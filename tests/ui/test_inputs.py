"""CSV and manual-entry parsing for the batch-triage UI (spec FR-001..FR-004, FR-010, FR-013)."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit")

from aml_triage.ui.inputs import (  # noqa: E402
    OPTIONAL_DEFAULTS,
    REQUIRED_COLUMNS,
    SCHEMA_COLUMNS,
    StructuralError,
    parse_manual_rows,
    read_csv_rows,
)

HEADER = ",".join(SCHEMA_COLUMNS)


def _csv(*rows: str, header: str = HEADER) -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode()


def test_schema_columns_match_the_request_schema() -> None:
    assert SCHEMA_COLUMNS[:7] == [
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    ]
    assert set(REQUIRED_COLUMNS) == set(SCHEMA_COLUMNS[:7])
    assert set(OPTIONAL_DEFAULTS) == set(SCHEMA_COLUMNS[7:])


def test_rows_keep_values_as_received_and_number_from_one(example_csv) -> None:
    rows = read_csv_rows(example_csv, limit=5000)
    assert [r["input_row"] for r in rows] == list(range(1, len(rows) + 1))
    assert rows[0]["type"] == "CASH_OUT" and rows[0]["amount"] == "290.85"  # string, untouched
    assert rows[0]["dest_is_merchant"] is False  # booleans are the one parsed field
    assert set(rows[0]) == {"input_row", *SCHEMA_COLUMNS}


def test_header_whitespace_and_case_are_normalised() -> None:
    header = " Step , TYPE ,amount,oldbalanceorg,NewBalanceOrig,oldbalanceDest ,newbalanceDest"
    rows = read_csv_rows(_csv("1,PAYMENT,10,100,90,0,0", header=header), limit=10)
    assert rows[0]["step"] == "1" and rows[0]["oldbalanceOrg"] == "100"


def test_optional_columns_default_when_absent_or_blank() -> None:
    header = ",".join(REQUIRED_COLUMNS) + ",dest_is_merchant"
    rows = read_csv_rows(_csv("1,PAYMENT,10,100,90,0,0,", header=header), limit=10)
    assert rows[0]["orig_prior_txn_count"] == 0 and rows[0]["dest_prior_amount_sum"] == 0.0
    assert rows[0]["dest_is_merchant"] is False


@pytest.mark.parametrize(
    "raw,expected",
    [("true", True), ("FALSE", False), ("1", True), ("0", False), ("Yes", True), ("no", False)],
)
def test_merchant_flag_parsing(raw: str, expected: bool) -> None:
    rows = read_csv_rows(_csv(f"1,PAYMENT,10,100,90,0,0,0,0,0,0,{raw}"), limit=10)
    assert rows[0]["dest_is_merchant"] is expected


def test_unknown_columns_refuse_the_file(csv_unknown_column) -> None:
    with pytest.raises(StructuralError) as exc:
        read_csv_rows(csv_unknown_column, limit=5000)
    assert exc.value.kind == "unknown_columns" and "nameOrig_amount" in exc.value.detail["cols"]


def test_missing_required_column_refuses_the_file() -> None:
    header = ",".join(c for c in REQUIRED_COLUMNS if c != "amount")
    with pytest.raises(StructuralError) as exc:
        read_csv_rows(_csv("1,PAYMENT,100,90,0,0", header=header), limit=10)
    assert exc.value.kind == "missing_columns" and "amount" in exc.value.detail["cols"]


def test_empty_and_header_only_files_are_refused(csv_header_only) -> None:
    for data in (b"", csv_header_only):
        with pytest.raises(StructuralError) as exc:
            read_csv_rows(data, limit=10)
        assert exc.value.kind == "empty"


def test_over_limit_is_refused_with_the_limit(example_csv) -> None:
    with pytest.raises(StructuralError) as exc:
        read_csv_rows(example_csv, limit=3)
    assert exc.value.kind == "over_limit"
    assert exc.value.detail["limit"] == 3 and exc.value.detail["n"] > 3


def test_non_utf8_bytes_are_refused() -> None:
    with pytest.raises(StructuralError) as exc:
        read_csv_rows(b"\xff\xfe\x00\x00not csv", limit=10)
    assert exc.value.kind == "unreadable"


def test_manual_rows_with_header_equal_csv_rows(example_csv) -> None:
    text = example_csv.decode("utf-8")
    assert parse_manual_rows(text, limit=5000) == read_csv_rows(example_csv, limit=5000)


def test_manual_rows_without_header_use_schema_order() -> None:
    rows = parse_manual_rows("600,TRANSFER,250000,250000,0,0,250000\n", limit=10)
    assert rows[0]["type"] == "TRANSFER" and rows[0]["newbalanceOrig"] == "0"
    assert rows[0]["orig_prior_txn_count"] == 0 and rows[0]["input_row"] == 1


def test_manual_blank_text_is_empty() -> None:
    with pytest.raises(StructuralError) as exc:
        parse_manual_rows("   \n", limit=10)
    assert exc.value.kind == "empty"
