"""Causal prior-transaction aggregates (spec FR-032, research R-07).

Rows are ordered by ``(step, row_index)``. For each account identifier the aggregate for a row
uses only rows strictly earlier in that order, so a row never sees itself or any later row.
Limitation (documented): PaySim has no intra-step timestamps, so rows in the same step are
ordered by their file position; a row counts same-step rows that appear earlier in the file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ROW_INDEX = "row_index"
AGGREGATE_SPECS = {
    "orig_prior_txn_count": ("nameOrig", "count"),
    "orig_prior_amount_sum": ("nameOrig", "sum"),
    "dest_prior_txn_count": ("nameDest", "count"),
    "dest_prior_amount_sum": ("nameDest", "sum"),
}


def causal(df: pd.DataFrame) -> pd.DataFrame:  # registry entry point (returns all four columns)
    return causal_aggregates(df)


def causal_aggregates(df: pd.DataFrame, names: list[str] | None = None) -> pd.DataFrame:
    names = names or list(AGGREGATE_SPECS)
    row_index = df[ROW_INDEX].to_numpy() if ROW_INDEX in df.columns else np.arange(len(df))
    order = np.lexsort((row_index, df["step"].to_numpy()))  # primary key step, secondary row_index
    sdf = df.iloc[order]
    amount = sdf["amount"].astype("float64")
    out = pd.DataFrame(index=sdf.index)
    for name in names:
        id_col, kind = AGGREGATE_SPECS[name]
        grp = sdf.groupby(sdf[id_col].astype("string"), sort=False, observed=True)
        if kind == "count":
            out[name] = grp.cumcount().astype("int32")
        else:
            out[name] = (
                amount.groupby(sdf[id_col].astype("string"), sort=False, observed=True).cumsum()
                - amount
            ).astype("float64")
    return out.reindex(df.index)


def brute_force_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """O(n^2) reference implementation for tests."""
    row_index = df[ROW_INDEX].to_numpy() if ROW_INDEX in df.columns else np.arange(len(df))
    step = df["step"].to_numpy()
    amount = df["amount"].astype("float64").to_numpy()
    out = {k: np.zeros(len(df)) for k in AGGREGATE_SPECS}
    for id_col, prefix in (("nameOrig", "orig"), ("nameDest", "dest")):
        ids = df[id_col].astype(str).to_numpy()
        for i in range(len(df)):
            earlier = (ids == ids[i]) & (
                (step < step[i]) | ((step == step[i]) & (row_index < row_index[i]))
            )
            out[f"{prefix}_prior_txn_count"][i] = earlier.sum()
            out[f"{prefix}_prior_amount_sum"][i] = amount[earlier].sum()
    return pd.DataFrame(out, index=df.index)
