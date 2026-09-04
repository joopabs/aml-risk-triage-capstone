"""Schema loading and validation against configs/schema.yaml (spec FR-020)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_PANDAS_DTYPES = {
    "int8": "int8",
    "int16": "int16",
    "int32": "int32",
    "int64": "int64",
    "float32": "float32",
    "float64": "float64",
    "category": "category",
    "string": "string",
}


class SchemaError(ValueError):
    """Raised when a frame does not match the expected schema."""


@dataclass
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool = False
    min: float | None = None
    min_is_soft: bool = False
    allowed: list[Any] | None = None
    role: str = "feature"
    availability: str = "realtime"
    unit: str = ""
    description: str = ""


@dataclass
class Schema:
    columns: list[ColumnSpec]
    sensitive_attribute_names: list[str] = field(default_factory=list)
    balance_tolerance: float = 0.01

    @property
    def names(self) -> list[str]:
        return [c.name for c in self.columns]

    def by_role(self, role: str) -> list[str]:
        return [c.name for c in self.columns if c.role == role]

    def read_dtypes(self) -> dict[str, str]:
        """Dtype map for ``pd.read_csv`` (identifiers as pyarrow strings to save memory)."""
        out: dict[str, str] = {}
        for c in self.columns:
            if c.dtype == "string":
                out[c.name] = "string[pyarrow]"
            elif c.dtype == "category":
                out[c.name] = "category"
            else:
                out[c.name] = _PANDAS_DTYPES[c.dtype]
        return out


def load_schema(path: str | Path = "configs/schema.yaml") -> Schema:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    cols = []
    for name, spec in raw["columns"].items():
        if spec.get("dtype") not in _PANDAS_DTYPES:
            raise SchemaError(f"{name}: unsupported dtype {spec.get('dtype')!r}")
        cols.append(ColumnSpec(name=name, **spec))
    return Schema(
        columns=cols,
        sensitive_attribute_names=list(raw.get("sensitive_attribute_scan", {}).get("names", [])),
        balance_tolerance=float(raw.get("balance_tolerance", 0.01)),
    )


@dataclass
class SchemaReport:
    n_rows: int
    missing_columns: list[str]
    unexpected_columns: list[str]
    dtype_problems: dict[str, str]
    null_violations: dict[str, int]
    allowed_violations: dict[str, int]
    soft_min_violations: dict[str, int]
    hard_min_violations: dict[str, int]

    @property
    def ok(self) -> bool:
        return not (
            self.missing_columns
            or self.dtype_problems
            or self.null_violations
            or self.allowed_violations
            or self.hard_min_violations
        )

    def summary(self) -> str:
        lines = [f"rows: {self.n_rows}"]
        lines.append(f"missing columns: {self.missing_columns or 'none'}")
        lines.append(f"unexpected columns: {self.unexpected_columns or 'none'}")
        lines.append(f"dtype problems: {self.dtype_problems or 'none'}")
        lines.append(f"null violations: {self.null_violations or 'none'}")
        lines.append(f"allowed-value violations: {self.allowed_violations or 'none'}")
        lines.append(f"hard min violations: {self.hard_min_violations or 'none'}")
        lines.append(f"soft min violations (counted, not fatal): {self.soft_min_violations or 'none'}")
        return "\n".join(lines)


def _coercible(series: pd.Series, dtype: str) -> str | None:
    """Return None if the series can be represented as ``dtype``, else a reason."""
    try:
        if dtype.startswith(("int", "float")):
            numeric = pd.to_numeric(series, errors="coerce")
            bad = numeric.isna() & series.notna()
            if bad.any():
                return f"{int(bad.sum())} non-numeric value(s)"
            if dtype.startswith("int") and not (numeric.dropna() % 1 == 0).all():
                return "non-integer values"
        elif dtype in {"category", "string"}:
            series.astype("string")
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        return str(exc)
    return None


def validate_frame(df: pd.DataFrame, schema: Schema) -> SchemaReport:
    """Validate columns, coercibility, nullability, allowed values, and minimums."""
    present = list(df.columns)
    missing = [c for c in schema.names if c not in present]
    unexpected = [c for c in present if c not in schema.names]
    dtype_problems: dict[str, str] = {}
    null_violations: dict[str, int] = {}
    allowed_violations: dict[str, int] = {}
    soft_min: dict[str, int] = {}
    hard_min: dict[str, int] = {}
    for spec in schema.columns:
        if spec.name not in df.columns:
            continue
        s = df[spec.name]
        reason = _coercible(s, spec.dtype)
        if reason:
            dtype_problems[spec.name] = reason
            continue
        if not spec.nullable and int(s.isna().sum()):
            null_violations[spec.name] = int(s.isna().sum())
        if spec.allowed is not None:
            bad = int((~s.isin(spec.allowed) & s.notna()).sum())
            if bad:
                allowed_violations[spec.name] = bad
        if spec.min is not None and spec.dtype.startswith(("int", "float")):
            below = int((pd.to_numeric(s, errors="coerce") < spec.min).sum())
            if below:
                (soft_min if spec.min_is_soft else hard_min)[spec.name] = below
    return SchemaReport(
        n_rows=len(df),
        missing_columns=missing,
        unexpected_columns=unexpected,
        dtype_problems=dtype_problems,
        null_violations=null_violations,
        allowed_violations=allowed_violations,
        soft_min_violations=soft_min,
        hard_min_violations=hard_min,
    )


def assert_valid(df: pd.DataFrame, schema: Schema) -> SchemaReport:
    report = validate_frame(df, schema)
    if not report.ok:
        raise SchemaError("schema validation failed:\n" + report.summary())
    return report
