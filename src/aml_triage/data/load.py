"""Raw CSV loading with an explicit dtype map (memory-safe, research R-04)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aml_triage.data.schema import Schema, SchemaError, load_schema


def read_header(path: str | Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def load_raw(path: str | Path, schema: Schema | None = None, nrows: int | None = None) -> pd.DataFrame:
    """Read the raw CSV. Columns missing from the file raise ``SchemaError`` before any modeling."""
    schema = schema or load_schema()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"raw data file not found: {p} (run `make data`)")
    header = read_header(p)
    missing = [c for c in schema.names if c not in header]
    if missing:
        raise SchemaError(f"raw file is missing expected columns: {missing}")
    dtypes = {k: v for k, v in schema.read_dtypes().items() if k in header}
    # Read numerics as float64/int64 first so a corrupt value surfaces as a clear error, then downcast.
    read_dtypes = {
        k: ("float64" if v.startswith("float") else "int64" if v.startswith("int") else v)
        for k, v in dtypes.items()
    }
    df = pd.read_csv(p, dtype=read_dtypes, nrows=nrows)
    for col, target in dtypes.items():
        if target.startswith(("float", "int")) and df[col].dtype != target:
            df[col] = df[col].astype(target)
    return df
