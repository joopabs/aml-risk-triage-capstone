"""CSV exports for the batch-triage UI (contracts/export-format.md). Built in memory only."""

from __future__ import annotations

import csv
import io
from typing import Any

from aml_triage.constants import DISCLAIMER
from aml_triage.ui.inputs import SCHEMA_COLUMNS

QUEUE_HEADER = [
    "rank",
    "review_priority",
    "risk_score",
    "input_row",
    *SCHEMA_COLUMNS,
    "model_version",
]
SKIPPED_HEADER = ["input_row", "field", "reason", *SCHEMA_COLUMNS]
BOM = "﻿"


def file_names(model_version: str) -> tuple[str, str]:
    return f"triage_queue_{model_version}.csv", f"triage_skipped_{model_version}.csv"


def _echo(row: dict[str, Any] | None) -> list[Any]:
    if row is None:
        return [""] * len(SCHEMA_COLUMNS)
    return [row.get(c, "") for c in SCHEMA_COLUMNS]


def _render(header: list[str], lines: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    buf.write(BOM)
    buf.write("# " + DISCLAIMER + "\n")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(lines)
    return buf.getvalue().encode("utf-8")


def queue_csv(rows_in: list[dict[str, Any]], result: dict[str, Any]) -> bytes:
    by_input = {r["input_row"]: r for r in rows_in}
    scored = sorted(
        result["rows"],
        key=lambda r: (r["rank"] if r.get("rank") is not None else 0, r["input_row"]),
    )
    lines = [
        [
            "" if r.get("rank") is None else r["rank"],
            r["review_priority"],
            f"{float(r['risk_score']):.6f}",
            r["input_row"],
            *_echo(by_input.get(r["input_row"])),
            result["model_version"],
        ]
        for r in scored
    ]
    return _render(QUEUE_HEADER, lines)


def skipped_csv(rows_in: list[dict[str, Any]], result: dict[str, Any]) -> bytes:
    by_input = {r["input_row"]: r for r in rows_in}
    lines = [
        [
            issue["input_row"],
            issue["field"],
            issue["reason"],
            *_echo(by_input.get(issue["input_row"])),
        ]
        for issue in result["skipped"]
    ]
    return _render(SKIPPED_HEADER, lines)
