"""Input handling for the batch-triage UI: CSV upload and pasted rows (spec FR-001..FR-004, FR-013).

Values are passed through as received (strings), except the merchant flag, which is parsed to a
boolean when it is one of the accepted spellings. Row-level validation is the service's job
(skip and report); this module only enforces the structural rules: known columns, required
columns present, at least one data row, and the batch limit.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import pandas as pd

SCHEMA_COLUMNS: list[str] = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "orig_prior_txn_count",
    "orig_prior_amount_sum",
    "dest_prior_txn_count",
    "dest_prior_amount_sum",
    "dest_is_merchant",
]
REQUIRED_COLUMNS: list[str] = SCHEMA_COLUMNS[:7]
OPTIONAL_DEFAULTS: dict[str, Any] = {
    "orig_prior_txn_count": 0,
    "orig_prior_amount_sum": 0.0,
    "dest_prior_txn_count": 0,
    "dest_prior_amount_sum": 0.0,
    "dest_is_merchant": False,
}
_CANONICAL = {c.lower(): c for c in SCHEMA_COLUMNS}
_TRUE = {"true", "1", "yes", "y", "t"}
_FALSE = {"false", "0", "no", "n", "f"}


class StructuralError(ValueError):
    """The whole input is refused; ``kind`` selects the message, ``detail`` fills it."""

    def __init__(self, kind: str, **detail: Any):
        super().__init__(kind)
        self.kind = kind
        self.detail = detail


def normalise_header(columns: list[str]) -> tuple[list[str], list[str]]:
    """Canonical column names (case/whitespace-insensitive) and the unknown originals."""
    canonical: list[str] = []
    unknown: list[str] = []
    for c in columns:
        key = c.strip().lower()
        if key in _CANONICAL:
            canonical.append(_CANONICAL[key])
        else:
            unknown.append(c.strip())
    return canonical, unknown


def parse_bool(value: Any) -> Any:
    """Accepted spellings become bool; anything else is returned untouched for the service to report."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return value


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StructuralError("unreadable") from exc


def _rows_from_records(records: list[dict[str, str]], limit: int) -> list[dict[str, Any]]:
    if not records:
        raise StructuralError("empty")
    if len(records) > limit:
        raise StructuralError("over_limit", n=len(records), limit=limit)
    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(records, start=1):
        row: dict[str, Any] = {"input_row": i}
        for col in SCHEMA_COLUMNS:
            raw = rec.get(col)
            value = raw.strip() if isinstance(raw, str) else raw
            if col in OPTIONAL_DEFAULTS and (value is None or value == ""):
                value = OPTIONAL_DEFAULTS[col]
            elif value is None:
                value = ""
            if col == "dest_is_merchant":
                value = parse_bool(value)
            row[col] = value
        rows.append(row)
    return rows


def read_csv_rows(data: bytes, limit: int) -> list[dict[str, Any]]:
    """Parse an uploaded CSV into request rows; raise StructuralError for whole-file problems."""
    text = _decode(data)
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise StructuralError("empty") from exc
    if not any(h.strip() for h in header):
        raise StructuralError("empty")
    canonical, unknown = normalise_header(header)
    if unknown:
        raise StructuralError("unknown_columns", cols=unknown)
    missing = [c for c in REQUIRED_COLUMNS if c not in canonical]
    if missing:
        raise StructuralError("missing_columns", cols=missing)
    records: list[dict[str, str]] = []
    for values in reader:
        if not any(v.strip() for v in values):
            continue
        rec = dict(zip(canonical, values, strict=False))
        for extra in values[len(canonical) :]:
            if extra.strip():
                raise StructuralError("unknown_columns", cols=["<unnamed column>"])
        records.append(rec)
    return _rows_from_records(records, limit)


def parse_manual_rows(text: str, limit: int) -> list[dict[str, Any]]:
    """Pasted rows: a CSV with header, or header-less lines in schema order (required first)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise StructuralError("empty")
    first = next(csv.reader([lines[0]]))
    canonical, unknown = normalise_header(first)
    looks_like_header = not unknown and "type" in canonical and "amount" in canonical
    if looks_like_header:
        return read_csv_rows("\n".join(lines).encode("utf-8"), limit)
    n = len(first)
    if n < len(REQUIRED_COLUMNS):
        raise StructuralError(
            "missing_columns", cols=REQUIRED_COLUMNS[n:] if n < len(REQUIRED_COLUMNS) else []
        )
    if n > len(SCHEMA_COLUMNS):
        raise StructuralError("unknown_columns", cols=[f"column {n}"])
    header = ",".join(SCHEMA_COLUMNS[:n])
    return read_csv_rows(("\n".join([header, *lines])).encode("utf-8"), limit)


def rows_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Typed view of the input rows for display and export joins (does not alter ``rows``)."""
    df = pd.DataFrame(rows)
    for col in ("amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "step" in df:
        df["step"] = pd.to_numeric(df["step"], errors="coerce")
    return df
