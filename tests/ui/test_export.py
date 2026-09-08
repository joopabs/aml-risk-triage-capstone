"""Export format tests (specs/002-batch-triage-ui/contracts/export-format.md)."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pytest
import yaml

pytest.importorskip("streamlit")

from aml_triage.constants import DISCLAIMER, PROHIBITED_OUTPUT_FIELDS  # noqa: E402
from aml_triage.ui.export import file_names, queue_csv, skipped_csv  # noqa: E402
from aml_triage.ui.inputs import SCHEMA_COLUMNS, read_csv_rows  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

QUEUE_HEADER = [
    "rank",
    "review_priority",
    "risk_score",
    "input_row",
    *SCHEMA_COLUMNS,
    "model_version",
]
SKIPPED_HEADER = ["input_row", "field", "reason", *SCHEMA_COLUMNS]


@pytest.fixture
def scored(ui_client, csv_with_invalid_rows):
    rows = read_csv_rows(csv_with_invalid_rows, limit=5000)
    result = ui_client.score_batch(rows, "all")
    return rows, result


def _parse(data: bytes) -> tuple[str, list[str], list[list[str]]]:
    text = data.decode("utf-8-sig")
    lines = text.splitlines()
    reader = list(csv.reader(io.StringIO("\n".join(lines[1:]))))
    return lines[0], reader[0], reader[1:]


def test_first_line_is_the_disclaimer_and_bom_present(scored) -> None:
    rows, result = scored
    for data in (queue_csv(rows, result), skipped_csv(rows, result)):
        assert data.startswith("﻿".encode())
        first, _, _ = _parse(data)
        assert first == "# " + DISCLAIMER


def test_queue_layout_and_order(scored) -> None:
    rows, result = scored
    _, header, body = _parse(queue_csv(rows, result))
    assert header == QUEUE_HEADER
    assert len(body) == result["counts"]["scored"]
    ranks = [int(r[0]) for r in body]
    assert ranks == sorted(ranks) == list(range(1, len(body) + 1))
    by_input = {r["input_row"]: r for r in rows}
    for line in body:
        rec = dict(zip(header, line, strict=True))
        src = by_input[int(rec["input_row"])]
        assert rec["type"] == src["type"] and rec["amount"] == str(
            src["amount"]
        )  # echoed as received
        assert rec["model_version"] == result["model_version"]
        assert re.fullmatch(r"\d\.\d{6}", rec["risk_score"])


def test_skipped_layout(scored) -> None:
    rows, result = scored
    _, header, body = _parse(skipped_csv(rows, result))
    assert header == SKIPPED_HEADER
    assert len(body) == len(result["skipped"])
    by_input = {r["input_row"]: r for r in rows}
    for line in body:
        rec = dict(zip(header, line, strict=True))
        assert rec["field"] and rec["reason"]
        assert rec["type"] == str(by_input[int(rec["input_row"])]["type"])


def test_no_prohibited_fields_or_vocabulary(scored) -> None:
    rows, result = scored
    vocab = yaml.safe_load((REPO_ROOT / "configs" / "vocabulary.yaml").read_text())
    for data in (queue_csv(rows, result), skipped_csv(rows, result)):
        _, header, body = _parse(data)
        assert not (set(h.lower() for h in header) & set(PROHIBITED_OUTPUT_FIELDS))
        text = data.decode("utf-8-sig").replace(DISCLAIMER, " ")
        for phrase in vocab["prohibited_applied_to_outputs"]:
            assert not re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE)


def test_file_names_carry_the_model_version(scored) -> None:
    _, result = scored
    queue_name, skipped_name = file_names(result["model_version"])
    assert queue_name == f"triage_queue_{result['model_version']}.csv"
    assert skipped_name == f"triage_skipped_{result['model_version']}.csv"
