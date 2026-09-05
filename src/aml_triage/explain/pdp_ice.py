"""PDP/ICE for the top SHAP features with validity checks (spec FR-062). Permutation importance is the
documented alternative when a partial-dependence view would mislead."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import PartialDependenceDisplay, permutation_importance

from aml_triage.config import Config
from aml_triage.explain.captions import human_name
from aml_triage.reporting.figures import apply_style, save_figure

warnings.filterwarnings("ignore", message="No positive class found in y_true")

CORR_THRESHOLD = 0.8


def validity(
    X: pd.DataFrame, top: list[str], threshold: float = CORR_THRESHOLD
) -> list[dict[str, Any]]:
    """For each top feature: produced unless it is strongly rank-correlated with another top feature."""
    corr = X[top].corr(method="spearman").abs()
    out = []
    for f in top:
        others = corr[f].drop(f)
        partner, rho = (others.idxmax(), float(others.max())) if len(others) else (None, 0.0)
        binary = X[f].nunique() <= 2
        if rho > threshold:
            out.append(
                {
                    "feature": f,
                    "status": "omitted",
                    "reason": f"|Spearman ρ| = {rho:.2f} with `{partner}` exceeds {threshold}; a partial-dependence curve would vary one while holding a near-duplicate fixed, producing implausible inputs",
                    "alternative": "permutation importance (below) and the SHAP dependence of the pair",
                }
            )
        else:
            out.append(
                {
                    "feature": f,
                    "status": "produced",
                    "reason": (
                        "binary flag: the curve has two points"
                        if binary
                        else f"max |Spearman ρ| with other top features = {rho:.2f}"
                    ),
                    "alternative": None,
                }
            )
    return out


def run_pdp_ice(
    cfg: Config, estimator, X_eval: pd.DataFrame, y_eval: pd.Series, top: list[str], version: str
) -> dict[str, Any]:
    apply_style()
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "explain"
    checks = validity(X_eval, top)
    produced = [c["feature"] for c in checks if c["status"] == "produced"]
    rng = np.random.default_rng(cfg.seed)
    X_eval = X_eval.astype("float64")  # scikit-learn refuses integer columns for partial dependence
    sub = X_eval.iloc[rng.choice(len(X_eval), size=min(500, len(X_eval)), replace=False)]
    figures = []
    if produced:
        n = len(produced)
        cols = min(3, n)
        rows = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows), squeeze=False)
        disp = PartialDependenceDisplay.from_estimator(
            estimator,
            sub,
            produced,
            kind="both",
            subsample=150,
            grid_resolution=25,
            ax=axes.ravel()[:n],
            random_state=cfg.seed,
            ice_lines_kw={"alpha": 0.15, "linewidth": 0.6},
            pd_line_kw={"color": "#DD5143", "linewidth": 2.5},
        )
        for ax, f in zip(axes.ravel(), produced, strict=False):
            ax.set_xlabel(human_name(f))
            ax.set_ylabel("partial dependence (probability)")
        for ax in axes.ravel()[n:]:
            ax.axis("off")
        fig.suptitle(f"PDP (red) and ICE (thin) on a seeded test sample, {version}", y=1.01)
        fig.tight_layout()
        figures.append(
            str(
                save_figure(
                    fig,
                    fig_dir / "pdp_ice_top_features.png",
                    "Average (PDP) and individual (ICE) response of the predicted probability to each feature; features strongly correlated with another top feature are omitted (see validity table).",
                )
            )
        )
        _ = disp
    # alternative / cross-check: permutation importance on the evaluation sample
    pi = permutation_importance(
        estimator,
        X_eval,
        y_eval,
        scoring="average_precision",
        n_repeats=5,
        random_state=cfg.seed,
        n_jobs=cfg.compute.n_jobs,
    )
    perm = pd.DataFrame(
        {
            "feature": X_eval.columns,
            "mean_drop_in_pr_auc": pi.importances_mean,
            "std": pi.importances_std,
        }
    ).sort_values("mean_drop_in_pr_auc", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    top_perm = perm.head(15).iloc[::-1]
    ax.barh(
        [human_name(f) for f in top_perm["feature"]],
        top_perm["mean_drop_in_pr_auc"],
        xerr=top_perm["std"],
        color="#4C72B0",
    )
    ax.set_xlabel("mean drop in PR-AUC when the feature is permuted (5 repeats)")
    ax.set_title(f"Permutation importance, seeded test sample, {version}")
    figures.append(
        str(
            save_figure(
                fig,
                fig_dir / "permutation_importance.png",
                "Model-agnostic alternative to PDP for correlated features; a near-zero drop means the model can recover the signal from correlated features.",
            )
        )
    )
    return {
        "validity": checks,
        "produced": produced,
        "permutation_importance": perm.to_dict(orient="records"),
        "figures": figures,
    }
