"""Consistent figure styling and a save helper that stamps caption and disclaimer on every figure."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from aml_triage.constants import DISCLAIMER  # noqa: E402
from aml_triage.utils.io import ensure_dir  # noqa: E402

PALETTE = {"normal": "#4C72B0", "positive": "#DD5143"}
CLASS_LABELS = {0: "simulated normal", 1: "simulated fraud"}
SHORT_DISCLAIMER = (
    "Synthetic PaySim data; educational decision-support prototype; no AML determination."
)


def apply_style() -> None:
    sns.set_theme(style="whitegrid", context="notebook", font_scale=0.9)
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 130, "axes.titleweight": "bold"})


def save_figure(fig: plt.Figure, path: str | Path, caption: str) -> Path:
    """Add a wrapped caption plus the short disclaimer as a footnote, save PNG, close."""
    p = Path(path)
    ensure_dir(p.parent)
    footer = textwrap.fill(caption, 120) + "\n" + SHORT_DISCLAIMER
    fig.text(0.01, -0.02, footer, ha="left", va="top", fontsize=7.5, color="#444444", wrap=True)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def full_disclaimer() -> str:
    return DISCLAIMER
