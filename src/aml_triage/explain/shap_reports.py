"""SHAP global and local explanations for the released bundle (spec FR-060/FR-061)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from aml_triage.config import Config
from aml_triage.evaluation.capacity import rank_within_periods
from aml_triage.explain.captions import global_caption, human_name, local_caption
from aml_triage.features.pipeline import load_feature_matrix
from aml_triage.reporting.figures import apply_style, save_figure
from aml_triage.utils.io import load_joblib, read_json


def load_bundle(cfg: Config, model: str = "LATEST") -> tuple[dict[str, Any], str]:
    models_dir = Path(cfg.paths.models_dir)
    version = (models_dir / "LATEST").read_text().strip() if model == "LATEST" else model
    bundle = load_joblib(models_dir / version / "pipeline.joblib")
    return bundle, version


def choose_explainer(estimator, background: pd.DataFrame) -> tuple[Any, str, str]:
    """Return (explainer, name, units). Tree models → exact TreeExplainer (log-odds);
    linear pipelines → LinearExplainer on the scaled space; anything else → model-agnostic."""
    est = estimator
    if isinstance(est, Pipeline):
        final = est.steps[-1][1]
        if final.__class__.__name__ == "LogisticRegression":
            scaler = Pipeline(est.steps[:-1])
            bg = scaler.transform(background)
            return shap.LinearExplainer(final, bg), "LinearExplainer (scaled inputs)", "log-odds"
    cls = est.__class__.__name__
    if any(
        k in cls
        for k in ("HistGradientBoosting", "RandomForest", "GradientBoosting", "XGB", "LGBM")
    ):
        try:
            return shap.TreeExplainer(est), "TreeExplainer (exact)", "log-odds"
        except Exception:  # pragma: no cover - fall through to model-agnostic
            pass
    return (
        shap.Explainer(lambda X: est.predict_proba(X)[:, 1], background, seed=0),
        "PermutationExplainer (predict_proba)",
        "probability",
    )


def _shap_values(explainer, estimator, X: pd.DataFrame, name: str) -> np.ndarray:
    if name.startswith("LinearExplainer"):
        Xs = Pipeline(estimator.steps[:-1]).transform(X)
        vals = explainer.shap_values(Xs)
    else:
        vals = (
            explainer(X).values
            if not name.startswith("TreeExplainer")
            else explainer.shap_values(X)
        )
    vals = np.asarray(vals)
    if vals.ndim == 3:  # (n, features, classes) → positive class
        vals = vals[:, :, -1]
    if isinstance(vals, list):  # older API: [neg, pos]
        vals = np.asarray(vals[-1])
    return vals


def run_shap(cfg: Config, model: str = "LATEST") -> dict[str, Any]:
    apply_style()
    bundle, version = load_bundle(cfg, model)
    est, fset = bundle["estimator"], bundle["feature_set"]
    processed = Path(cfg.paths.processed_dir)
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "explain"
    rng = np.random.default_rng(cfg.seed)

    X_train, _ = load_feature_matrix(processed, fset, "train")
    background = X_train.iloc[
        rng.choice(
            len(X_train), size=min(cfg.explain.shap_background_rows, len(X_train)), replace=False
        )
    ]
    del X_train
    X_test, meta_test = load_feature_matrix(processed, fset, "test")
    features = list(X_test.columns)
    assert features == bundle["feature_list"], "feature order differs from the released bundle"

    explainer, name, units = choose_explainer(est, background)
    eval_idx = rng.choice(
        len(X_test), size=min(cfg.explain.shap_eval_rows, len(X_test)), replace=False
    )
    X_eval = X_test.iloc[eval_idx]
    vals = _shap_values(explainer, est, X_eval, name)
    mean_abs = pd.Series(np.abs(vals).mean(axis=0), index=features).sort_values(ascending=False)

    # global figures
    fig, ax = plt.subplots(figsize=(8, 6))
    mean_abs.iloc[::-1].plot(kind="barh", ax=ax, color="#4C72B0")
    ax.set_xlabel(f"mean |SHAP| ({units})")
    ax.set_title(f"Global feature importance, {version} (seeded test sample n={len(X_eval):,})")
    bar = save_figure(
        fig,
        fig_dir / "shap_01_global_bar.png",
        global_caption(list(mean_abs.head(5).items()), f"mean |SHAP| in {units}"),
    )
    plt.figure(figsize=(9, 6))
    shap.summary_plot(
        vals, X_eval, feature_names=[human_name(f) for f in features], show=False, max_display=15
    )
    fig = plt.gcf()
    fig.suptitle(f"SHAP summary (beeswarm), {version}", y=1.02)
    swarm = save_figure(
        fig,
        fig_dir / "shap_02_summary_beeswarm.png",
        f"Each point is one sampled test transaction; colour is the feature value; x is the contribution in {units}.",
    )

    # local: top-K rows of the first test review period, ranked by raw score
    _, preds = _selected_predictions(cfg, bundle)
    ranked = rank_within_periods(
        preds[["row_index", "step", "isFraud", "score"]], cfg.review.review_period_steps
    )
    first_period = ranked["period"].min()
    top = ranked[(ranked["period"] == first_period)].nsmallest(cfg.explain.n_local_examples, "rank")
    pos = meta_test.reset_index(drop=True)
    locals_out = []
    for r in top.itertuples():
        i = int(pos.index[pos["row_index"] == r.row_index][0])
        x = X_test.iloc[[i]]
        v = _shap_values(explainer, est, x, name)[0]
        base = (
            float(np.ravel(explainer.expected_value)[-1])
            if hasattr(explainer, "expected_value")
            else 0.0
        )
        order = np.argsort(-np.abs(v))
        contribs = [(features[j], float(x.iloc[0, j]), float(v[j])) for j in order[:3]]
        caption = local_caption(
            contribs,
            float(r.score),
            int(r.rank),
            f"test review period 1 (simulated day {int(first_period) + 1})",
            units,
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        ex = shap.Explanation(
            values=v,
            base_values=base,
            data=x.iloc[0].to_numpy(),
            feature_names=[human_name(f) for f in features],
        )
        shap.plots.waterfall(ex, max_display=10, show=False)
        fig = plt.gcf()
        fig.set_size_inches(9, 6)
        path = save_figure(fig, fig_dir / f"shap_local_rank{int(r.rank)}.png", caption)
        locals_out.append(
            {
                "rank": int(r.rank),
                "row_index": int(r.row_index),
                "step": int(r.step),
                "type": str(pos.loc[i, "type"]),
                "score": float(r.score),
                "top_contributions": [
                    {"feature": f, "value": val, "contribution": c} for f, val, c in contribs
                ],
                "caption": caption,
                "figure": str(path),
            }
        )

    return {
        "model_version": version,
        "candidate_id": bundle["candidate_id"],
        "feature_set": fset,
        "explainer": name,
        "units": units,
        "background_rows": int(len(background)),
        "eval_rows": int(len(X_eval)),
        "global_mean_abs_shap": {k: float(v) for k, v in mean_abs.items()},
        "global_figures": [str(bar), str(swarm)],
        "local_examples": locals_out,
        "eval_sample": {"X": X_eval, "values": vals},  # in-memory for PDP validity (not serialised)
    }


def _selected_predictions(
    cfg: Config, bundle: dict[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    from aml_triage.models.train import load_run, run_id

    return load_run(cfg, run_id(bundle["candidate_id"], bundle["feature_set"]), "test")


__all__ = ["run_shap", "choose_explainer", "load_bundle", "read_json"]
