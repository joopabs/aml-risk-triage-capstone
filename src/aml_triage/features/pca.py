"""PCA on standardised numeric training features (spec FR-035, research R-08).

Role (from config): diagnostic and visualisation. Components do not enter the primary candidates;
a ``pca_variant`` matrix (components + type one-hot) is written for one documented experiment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from aml_triage.config import Config
from aml_triage.data.split import SPLITS
from aml_triage.features.base import load_registry
from aml_triage.features.pipeline import (
    META_PREFIX,
    FitScopeRecorder,
    assert_fit_scope,
    load_feature_matrix,
)
from aml_triage.reporting.figures import CLASS_LABELS, PALETTE, apply_style, save_figure
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import save_joblib, write_json, write_parquet

NARRATIVE_FILENAME = "pca_narrative.md"


def pca_input_columns(X: pd.DataFrame, registry_path: str | Path) -> tuple[list[str], list[str]]:
    kinds = {d.name: d.kind for d in load_registry(registry_path)}
    cols = [c for c in X.columns if kinds.get(c) in ("numeric", "aggregate")]
    constant = [c for c in cols if X[c].nunique() <= 1]
    return [c for c in cols if c not in constant], constant


def run_pca(cfg: Config, set_name: str = "primary", n_neg_sample: int = 200_000) -> dict[str, Any]:
    apply_style()
    processed = Path(cfg.paths.processed_dir)
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "features"
    X, meta = load_feature_matrix(processed, set_name, "train")
    y = meta["isFraud"].astype(int)
    cols, constant = pca_input_columns(X, cfg.features.registry)

    rec = FitScopeRecorder(
        Pipeline(
            [
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=cfg.pca.n_components, random_state=cfg.seed)),
            ]
        )
    )
    rec.fit(X[cols], split_id="train")
    pca: PCA = rec.transformer.named_steps["pca"]
    evr = pca.explained_variance_ratio_
    cum = np.cumsum(evr)
    loadings = pd.DataFrame(
        pca.components_.T, index=cols, columns=[f"PC{i + 1}" for i in range(pca.n_components_)]
    )

    # figures
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(1, len(evr) + 1), evr, color=PALETTE["normal"], label="explained variance ratio")
    ax.plot(range(1, len(cum) + 1), cum, color=PALETTE["positive"], marker="o", label="cumulative")
    ax.axhline(0.95, ls="--", color="grey", lw=1)
    ax.set_xlabel("component")
    ax.set_ylabel("variance ratio")
    ax.legend()
    ax.set_title(
        f"PCA scree on standardised training features ({len(cols)} inputs → {pca.n_components_} components at 95%)"
    )
    scree = save_figure(
        fig,
        fig_dir / "pca_01_scree.png",
        "Fitted on the training split only; inputs are numeric and aggregate features (flags and one-hots excluded).",
    )

    rng = np.random.default_rng(cfg.seed)
    pos_idx = y.index[y == 1].to_numpy()
    neg_idx = rng.choice(
        y.index[y == 0].to_numpy(), size=min(n_neg_sample, int((y == 0).sum())), replace=False
    )
    idx = np.concatenate([neg_idx, pos_idx])
    Z = rec.transform(X.loc[idx, cols], split_id="train")
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        Z[: len(neg_idx), 0],
        Z[: len(neg_idx), 1],
        s=3,
        alpha=0.3,
        c=PALETTE["normal"],
        linewidths=0,
        label=CLASS_LABELS[0],
    )
    ax.scatter(
        Z[len(neg_idx) :, 0],
        Z[len(neg_idx) :, 1],
        s=4,
        alpha=0.6,
        c=PALETTE["positive"],
        linewidths=0,
        label=CLASS_LABELS[1],
    )
    ax.set_xlabel(f"PC1 ({evr[0]:.1%})")
    ax.set_ylabel(f"PC2 ({evr[1]:.1%})")
    ax.legend(markerscale=4)
    ax.set_title("First two principal components, training sample (positives drawn last)")
    proj = save_figure(
        fig,
        fig_dir / "pca_02_projection.png",
        "Seeded sample: all training positives plus sampled negatives; projection uses the training-fitted scaler and PCA.",
    )

    # pca_variant matrices: components + type one-hot + meta, transform-only for val/test
    onehot = [c for c in X.columns if c.startswith("type_")]
    outputs = {}
    for split in SPLITS:
        Xs, ms = load_feature_matrix(processed, set_name, split)
        comps = pd.DataFrame(rec.transform(Xs[cols], split_id=split), columns=loadings.columns)
        frame = pd.concat(
            [
                comps,
                Xs[onehot].reset_index(drop=True),
                ms.add_prefix(META_PREFIX).reset_index(drop=True),
            ],
            axis=1,
        )
        outputs[split] = write_parquet(frame, processed / f"features_pca_variant_{split}.parquet")
    assert_fit_scope(rec.record())
    save_joblib(rec.transformer, processed / "feature_pipeline_pca_variant.joblib")
    write_json(rec.record(), processed / "feature_pipeline_pca_variant.fitscope.json")
    write_json(
        {
            "set": "pca_variant",
            "features": list(loadings.columns) + onehot,
            "inputs": cols,
            "source_set": set_name,
            "config_hash": cfg.config_hash(),
            "aggregates_included": False,
            "batch_only": [],
        },
        processed / "features_pca_variant.json",
    )

    result = {
        "role": cfg.pca.role,
        "n_components_target": cfg.pca.n_components,
        "n_components": int(pca.n_components_),
        "inputs": cols,
        "excluded_constant": constant,
        "explained_variance_ratio": [float(v) for v in evr],
        "cumulative": [float(v) for v in cum],
        "loadings": {pc: {f: float(loadings.loc[f, pc]) for f in cols} for pc in loadings.columns},
        "fit_scope": rec.record(),
        "figures": [str(scree), str(proj)],
        "pca_variant_outputs": {k: str(v) for k, v in outputs.items()},
        "config_hash": cfg.config_hash(),
    }
    write_json(result, Path(cfg.paths.reports_dir) / "pca_report.json")
    render_report(result, cfg.paths.reports_dir)
    return result


def render_report(result: dict[str, Any], reports_dir: str | Path) -> Path:
    reports = Path(reports_dir)
    ev_rows = [
        (f"PC{i + 1}", v, c)
        for i, (v, c) in enumerate(
            zip(result["explained_variance_ratio"], result["cumulative"], strict=True)
        )
    ]
    load_rows = []
    for pc, d in result["loadings"].items():
        top = sorted(d.items(), key=lambda kv: -abs(kv[1]))[:4]
        load_rows.append((pc, ", ".join(f"{f} ({v:+.2f})" for f, v in top)))
    rel = lambda p: Path(p).relative_to(reports) if Path(p).is_relative_to(reports) else Path(p)  # noqa: E731
    sections = [
        (
            "Role",
            f"Configured role: **{result['role']}**. Components are a diagnostic of feature redundancy and a "
            f"visualisation aid. They do not enter the primary model candidates. A `pca_variant` matrix "
            f"({result['n_components']} components plus type one-hot) is written for one documented experiment in Milestone 5.",
        ),
        (
            "Inputs",
            f"{len(result['inputs'])} standardised numeric/aggregate training features: "
            + ", ".join(f"`{c}`" for c in result["inputs"])
            + (
                f"\n\nExcluded as constant: {', '.join(f'`{c}`' for c in result['excluded_constant'])}"
                if result["excluded_constant"]
                else ""
            )
            + f"\n\nFit scope: {result['fit_scope']['fitted_on']} (scaler and PCA fitted on training rows only).",
        ),
        (
            f"Explained variance ({result['n_components']} components reach the {result['n_components_target']} target)",
            md_table(["component", "variance ratio", "cumulative"], ev_rows),
        ),
        (
            "Top loadings per component",
            md_table(["component", "largest absolute loadings"], load_rows),
        ),
        ("Figures", "\n\n".join(f"![{Path(p).stem}]({rel(p)})" for p in result["figures"])),
    ]
    sections += narrative_sections(
        reports / NARRATIVE_FILENAME,
        "<!-- Task T041: write reports/pca_narrative.md after reviewing the tables and figures above. -->\n\n_Pending review (task T041)._",
    )
    return write_markdown(reports / "pca_report.md", "PCA Report", sections)
