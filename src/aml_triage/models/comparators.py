"""Ranking comparators that require no training (research R-10).

* ``random_rank`` — seeded uniform scores: the primary null hypothesis.
* ``rule_rank``   — rule-flag rows first, then amount descending (the dataset's ``isFlaggedFraud``
  fires on 16 rows in total, so amount decides almost the whole ranking).
The dummy candidate is trained like a model; its constant scores rank as chronological order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def random_rank(meta: pd.DataFrame, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.random(len(meta)), index=meta.index, name="score")


def rule_rank(meta: pd.DataFrame, amount: pd.Series) -> pd.Series:
    """Score in [0, 2): flagged rows in [1, 2), unflagged in [0, 1); within each band by amount."""
    amt = amount.astype("float64").to_numpy()
    scaled = amt / (np.nanmax(amt) + 1.0) if len(amt) else amt
    flag = meta["isFlaggedFraud"].astype("float64").to_numpy()
    return pd.Series(flag + scaled, index=meta.index, name="score")
