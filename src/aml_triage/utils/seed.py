"""Global seeding so every stochastic component is reproducible (constitution Principle III)."""

from __future__ import annotations

import os
import random

import numpy as np


def set_global_seed(seed: int) -> np.random.Generator:
    """Seed Python, NumPy, and the hash seed; return a NumPy generator for local use.

    Estimators, samplers, splitters, and searches must still receive ``random_state=seed``
    explicitly; this function covers module-level randomness only.
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")
    random.seed(seed)
    np.random.seed(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    return np.random.default_rng(seed)
