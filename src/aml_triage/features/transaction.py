"""Transaction-level feature transforms. Each function is pure and vectorised: df -> Series."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

BALANCE_TOL = 0.01
INFLOW_TYPES = ("CASH_IN",)


def log1p_amount(df: pd.DataFrame) -> pd.Series:
    return np.log1p(df["amount"].astype("float64"))


def log1p_oldbalance_org(df: pd.DataFrame) -> pd.Series:
    return np.log1p(df["oldbalanceOrg"].astype("float64").clip(lower=0))


def log1p_oldbalance_dest(df: pd.DataFrame) -> pd.Series:
    return np.log1p(df["oldbalanceDest"].astype("float64").clip(lower=0))


def amount_to_orig_balance_ratio(df: pd.DataFrame) -> pd.Series:
    return df["amount"].astype("float64") / (df["oldbalanceOrg"].astype("float64") + 1.0)


def orig_zero_balance_flag(df: pd.DataFrame) -> pd.Series:
    return (df["oldbalanceOrg"] == 0).astype("int8")


def dest_zero_balance_flag(df: pd.DataFrame) -> pd.Series:
    return (df["oldbalanceDest"] == 0).astype("int8")


def zero_amount_flag(df: pd.DataFrame) -> pd.Series:
    return (df["amount"] == 0).astype("int8")


def dest_is_merchant(df: pd.DataFrame) -> pd.Series:
    return df["nameDest"].astype("string").str.startswith("M").fillna(False).astype("int8")


def step_hour_of_day(df: pd.DataFrame) -> pd.Series:
    return ((df["step"].astype("int64") - 1) % 24).astype("int8")


def step_day_index(df: pd.DataFrame) -> pd.Series:
    return ((df["step"].astype("int64") - 1) // 24).astype("int16")


def orig_balance_delta(df: pd.DataFrame) -> pd.Series:
    return df["oldbalanceOrg"].astype("float64") - df["newbalanceOrig"].astype("float64")


def dest_balance_delta(df: pd.DataFrame) -> pd.Series:
    return df["newbalanceDest"].astype("float64") - df["oldbalanceDest"].astype("float64")


def orig_balance_inconsistent_flag(df: pd.DataFrame, tol: float = BALANCE_TOL) -> pd.Series:
    inflow = df["type"].astype(str).isin(INFLOW_TYPES).to_numpy()
    old = df["oldbalanceOrg"].astype("float64").to_numpy()
    amt = df["amount"].astype("float64").to_numpy()
    expected = np.where(inflow, old + amt, old - amt)
    gap = np.abs(df["newbalanceOrig"].astype("float64").to_numpy() - expected)
    return pd.Series((gap > tol).astype("int8"), index=df.index)


def dest_balance_inconsistent_flag(df: pd.DataFrame, tol: float = BALANCE_TOL) -> pd.Series:
    gap = (
        df["newbalanceDest"].astype("float64")
        - df["oldbalanceDest"].astype("float64")
        - df["amount"].astype("float64")
    ).abs()
    return (gap > tol).astype("int8")


def orig_zero_after_flag(df: pd.DataFrame) -> pd.Series:
    return ((df["oldbalanceOrg"] > 0) & (df["newbalanceOrig"] == 0)).astype("int8")


class AmountBucketizer(BaseEstimator, TransformerMixin):
    """Quantile buckets for ``amount`` with edges fitted on the training split only."""

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins

    def fit(self, X, y=None):
        values = np.asarray(X, dtype="float64").ravel()
        qs = np.linspace(0, 1, self.n_bins + 1)[1:-1]
        self.edges_ = np.unique(np.quantile(values, qs))
        self.n_features_in_ = 1
        return self

    def transform(self, X):
        values = np.asarray(X, dtype="float64").ravel()
        out = np.searchsorted(self.edges_, values, side="right").astype("int16")
        return out.reshape(-1, 1)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(["amount_bucket"], dtype=object)
