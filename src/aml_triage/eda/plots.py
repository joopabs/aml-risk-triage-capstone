"""Applied EDA on the training split (spec FR-030). Descriptive time-series plots use all splits and
are labeled as descriptive; anything that could inform modeling decisions uses training rows only.

Human observations live in reports/eda_narrative.md (``### <figure file>`` blocks) and are merged
into reports/eda_summary.md so regeneration never erases them.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from aml_triage.config import Config
from aml_triage.data.split import MANIFEST_NAME, SplitManifest, load_split
from aml_triage.features.base import load_registry
from aml_triage.features.pipeline import load_feature_matrix
from aml_triage.reporting.figures import CLASS_LABELS, PALETTE, apply_style, save_figure
from aml_triage.reporting.tables import md_table, write_markdown

NARRATIVE_FILENAME = "eda_narrative.md"


def _sample(X: pd.DataFrame, y: pd.Series, n_neg: int, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    """All positives plus a seeded sample of negatives (for plots only, never for fitting)."""
    pos = y == 1
    neg_idx = y.index[~pos]
    rng = np.random.default_rng(seed)
    keep = np.concatenate(
        [
            y.index[pos].to_numpy(),
            rng.choice(neg_idx.to_numpy(), size=min(n_neg, len(neg_idx)), replace=False),
        ]
    )
    return X.loc[keep], y.loc[keep]


def _label(y: pd.Series) -> pd.Series:
    return y.map(CLASS_LABELS)


def run_eda(cfg: Config, n_neg_sample: int = 200_000) -> tuple[Path, list[tuple[str, str]]]:
    apply_style()
    processed = Path(cfg.paths.processed_dir)
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "eda"
    manifest = SplitManifest.read(processed / MANIFEST_NAME)
    registry = {d.name: d for d in load_registry(cfg.features.registry)}
    X, meta = load_feature_matrix(processed, "primary", "train")
    y = meta["isFraud"].astype(int)
    ttype = meta["type"].astype(str)
    Xs, ys = _sample(X, y, n_neg_sample, cfg.seed)
    ts = ttype.loc[Xs.index]
    figures: list[tuple[str, str]] = []
    pal = [PALETTE["normal"], PALETTE["positive"]]
    hue_order = [CLASS_LABELS[0], CLASS_LABELS[1]]

    # 1. class balance by type (train)
    ct = pd.crosstab(ttype, y)
    ct.columns = [CLASS_LABELS[c] for c in ct.columns]
    rate = (ct[CLASS_LABELS[1]] / ct.sum(axis=1)).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4))
    ct.plot(kind="bar", stacked=True, ax=ax, color=pal, logy=True)
    for i, (t, r) in enumerate(rate.items()):
        ax.text(i, ct.loc[t].sum() * 1.3, f"{r:.3%}", ha="center", fontsize=8)
    ax.set_title("Training rows by transaction type and class (log scale); label = positive rate")
    ax.set_xlabel("type")
    ax.set_ylabel("rows")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_01_class_by_type.png",
                    "Training split only. Positive rate per type annotated above each bar.",
                )
            ),
            "Class balance by type",
        )
    )

    # 2. amount distribution by class
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(
        x=Xs["log_amount"],
        hue=_label(ys),
        hue_order=hue_order,
        palette=pal,
        stat="density",
        common_norm=False,
        bins=60,
        element="step",
        ax=ax,
    )
    ax.set_title("log1p(amount) by class (density, training sample)")
    ax.set_xlabel("log1p(amount)")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_02_amount_by_class.png",
                    "All training positives plus a seeded sample of negatives; densities normalised per class.",
                )
            ),
            "Amount by class",
        )
    )

    # 3. amount by type and class
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.boxplot(
        x=ts,
        y=Xs["log_amount"],
        hue=_label(ys),
        hue_order=hue_order,
        palette=pal,
        ax=ax,
        fliersize=1,
        linewidth=0.8,
    )
    ax.set_title("log1p(amount) by type and class (training sample)")
    ax.set_xlabel("type")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_03_amount_by_type_class.png",
                    "Box plots on the training sample; types without positives show a single box.",
                )
            ),
            "Amount by type and class",
        )
    )

    # 4. volume and positives over time (descriptive, all splits, boundaries shaded)
    frames = [
        load_split(processed, s)[["step", "isFraud"]].assign(split=s)
        for s in ("train", "val", "test")
    ]
    allf = pd.concat(frames)
    allf["day"] = (allf["step"] - 1) // 24 + 1
    daily = allf.groupby("day").agg(rows=("isFraud", "size"), positives=("isFraud", "sum"))
    daily["prevalence"] = daily["positives"] / daily["rows"]
    fig, ax1 = plt.subplots(figsize=(10, 4.5))
    ax1.bar(
        daily.index, daily["rows"], color=PALETTE["normal"], alpha=0.6, label="transactions per day"
    )
    ax1.set_yscale("log")
    ax1.set_ylabel("transactions per day (log)")
    ax1.set_xlabel("simulated day")
    ax2 = ax1.twinx()
    ax2.plot(
        daily.index,
        daily["positives"],
        color=PALETTE["positive"],
        marker="o",
        ms=3,
        label="positives per day",
    )
    ax2.set_ylabel("positives per day")
    for bound, name in (
        (manifest.train_end_step, "train | val"),
        (manifest.val_end_step, "val | test"),
    ):
        if bound:
            d = (bound - 1) // 24 + 1 + 0.5
            ax1.axvline(d, color="black", ls="--", lw=1)
            ax1.text(d, daily["rows"].max(), name, rotation=90, va="top", ha="right", fontsize=8)
    ax1.set_title(
        "Descriptive: daily volume (bars, log) vs positives (line), all splits, split boundaries dashed"
    )
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8)
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_04_volume_positives_over_time.png",
                    "Descriptive view across all splits (no modeling decision). Positives arrive at a near-constant rate while volume varies by three orders of magnitude (DQ-10).",
                )
            ),
            "Volume and positives over time",
        )
    )

    # 5. prevalence by day
    fig, ax = plt.subplots(figsize=(10, 3.8))
    colors = daily.index.map(
        lambda d: (
            PALETTE["normal"]
            if (d - 1) * 24 + 1 <= (manifest.train_end_step or 0)
            else (
                "#8172B2"
                if (d - 1) * 24 + 1 <= (manifest.val_end_step or 0)
                else PALETTE["positive"]
            )
        )
    )
    ax.bar(daily.index, daily["prevalence"], color=list(colors))
    ax.set_yscale("log")
    ax.set_title(
        "Descriptive: positive prevalence per day (log), colored by split: train / val / test"
    )
    ax.set_xlabel("simulated day")
    ax.set_ylabel("prevalence")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_05_prevalence_by_day.png",
                    "Prevalence per simulated day; blue = train, purple = validation, red = test.",
                )
            ),
            "Prevalence by day",
        )
    )

    # 6. correlation heatmap (train sample, Spearman, numeric features + label)
    numeric = [c for c in Xs.columns if not c.startswith("type_")]
    corr = pd.concat([Xs[numeric], ys.rename("isFraud")], axis=1).corr(method="spearman")
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        corr,
        cmap="vlag",
        center=0,
        vmin=-1,
        vmax=1,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 6.5},
        square=True,
        cbar_kws={"shrink": 0.7},
        ax=ax,
    )
    ax.set_title("Spearman correlation of engineered features and label (training sample)")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_06_correlation_heatmap.png",
                    "Rank correlation on the training sample (all positives plus sampled negatives); the isFraud row is inflated by the sampling ratio and is for direction only.",
                )
            ),
            "Correlation heatmap",
        )
    )

    # 7. class-conditional distributions of numeric features (small multiples)
    cont = [
        c
        for c in numeric
        if registry.get(c, None) is not None and registry[c].kind in ("numeric", "aggregate")
    ]
    n = len(cont)
    cols = 4
    rows_n = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows_n, cols, figsize=(4 * cols, 3 * rows_n))
    for ax, c in zip(axes.ravel(), cont, strict=False):
        v = Xs[c].astype("float64")
        if (v >= 0).all() and v.max() > 100:
            v = np.log1p(v)
            label = f"log1p({c})"
        else:
            label = c
        sns.histplot(
            x=v,
            hue=_label(ys),
            hue_order=hue_order,
            palette=pal,
            stat="density",
            common_norm=False,
            bins=40,
            element="step",
            ax=ax,
            legend=False,
        )
        ax.set_title(label, fontsize=9)
        ax.set_xlabel("")
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle(
        "Class-conditional distributions of numeric features (training sample; blue normal, red positive)",
        y=1.01,
    )
    fig.tight_layout()
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_07_feature_distributions.png",
                    "Per-feature densities by class on the training sample; heavy-tailed features shown on log1p scale.",
                )
            ),
            "Feature distributions by class",
        )
    )

    # 8. flag features: positive rate when flag = 1 vs 0 (full train)
    flags = [c for c in X.columns if registry.get(c) is not None and registry[c].kind == "flag"]
    rows = []
    for c in flags:
        for v in (0, 1):
            m = X[c] == v
            rows.append(
                {
                    "flag": c,
                    "value": str(v),
                    "n": int(m.sum()),
                    "positive_rate": float(y[m].mean()) if m.any() else np.nan,
                }
            )
    fr = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.barplot(
        data=fr,
        x="flag",
        y="positive_rate",
        hue="value",
        palette=["#999999", PALETTE["positive"]],
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_title("Positive rate when flag = 0 vs flag = 1 (full training split, log scale)")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=25)
    for p_, (_, r) in zip(ax.patches, fr.iterrows(), strict=False):
        if np.isfinite(r["positive_rate"]) and r["positive_rate"] > 0:
            ax.text(
                p_.get_x() + p_.get_width() / 2,
                r["positive_rate"],
                f"n={r['n']:,}",
                ha="center",
                va="bottom",
                fontsize=6.5,
                rotation=90,
            )
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_08_flag_positive_rates.png",
                    "Full training split. Bars labeled with row counts; a missing bar means zero positives for that value.",
                )
            ),
            "Flag positive rates",
        )
    )
    flag_table = fr.copy()

    # 9. scatter amount vs origin balance
    fig, ax = plt.subplots(figsize=(7, 6))
    order = np.argsort(ys.to_numpy())  # positives drawn last
    ax.scatter(
        Xs["log_oldbalance_org"].to_numpy()[order],
        Xs["log_amount"].to_numpy()[order],
        c=[pal[int(v)] for v in ys.to_numpy()[order]],
        s=3,
        alpha=0.35,
        linewidths=0,
    )
    ax.set_xlabel("log1p(oldbalanceOrg)")
    ax.set_ylabel("log1p(amount)")
    ax.set_title("Amount vs origin balance before transaction (training sample; red = positive)")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_09_amount_vs_origbalance.png",
                    "Training sample; positives drawn on top. The diagonal is amount == origin balance (account emptied).",
                )
            ),
            "Amount vs origin balance",
        )
    )

    # 10. hour of day
    hod = pd.DataFrame({"hour": X["step_hour_of_day"].astype(int), "y": y})
    g = hod.groupby("hour").agg(rows=("y", "size"), rate=("y", "mean"))
    fig, ax1 = plt.subplots(figsize=(9, 3.8))
    ax1.bar(g.index, g["rows"], color=PALETTE["normal"], alpha=0.6)
    ax1.set_ylabel("rows")
    ax1.set_xlabel("hour of simulated day")
    ax2 = ax1.twinx()
    ax2.plot(g.index, g["rate"], color=PALETTE["positive"], marker="o", ms=3)
    ax2.set_ylabel("positive rate")
    ax2.set_yscale("log")
    ax1.set_title("Training rows (bars) and positive rate (line, log) by hour of simulated day")
    figures.append(
        (
            str(save_figure(fig, fig_dir / "eda_10_hour_of_day.png", "Training split only.")),
            "Hour of day",
        )
    )

    # 11. destination prior count by class
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(
        x=np.log1p(Xs["dest_prior_txn_count"].astype(float)),
        hue=_label(ys),
        hue_order=hue_order,
        palette=pal,
        stat="density",
        common_norm=False,
        bins=40,
        element="step",
        ax=ax,
    )
    ax.set_title("log1p(dest_prior_txn_count) by class (training sample)")
    ax.set_xlabel("log1p(prior transactions to the same destination)")
    figures.append(
        (
            str(
                save_figure(
                    fig,
                    fig_dir / "eda_11_dest_prior_count.png",
                    "Causal aggregate: earlier transactions to the same destination. Training sample.",
                )
            ),
            "Destination prior count",
        )
    )

    # summary tables
    per_type = pd.crosstab(ttype, y)
    per_type["positive_rate"] = per_type[1] / per_type.sum(axis=1)
    summary_path = write_summary(cfg, figures, per_type, flag_table, daily)
    return summary_path, figures


def _narrative(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    key, body = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if key:
                out[key] = "\n".join(body).strip()
            key, body = line[4:].strip(), []
        elif key is not None:
            body.append(line)
    if key:
        out[key] = "\n".join(body).strip()
    return out


def write_summary(
    cfg: Config,
    figures: list[tuple[str, str]],
    per_type: pd.DataFrame,
    flag_table: pd.DataFrame,
    daily: pd.DataFrame,
) -> Path:
    reports = Path(cfg.paths.reports_dir)
    notes = _narrative(reports / NARRATIVE_FILENAME)
    sections: list[tuple[str, str]] = [
        (
            "Scope",
            "Figures below use the **training split** (steps 1–408) unless labeled descriptive; class-conditional "
            "plots use all training positives plus a seeded sample of negatives. No modeling decision here "
            "uses validation or test rows. Observations are written by a human in `reports/eda_narrative.md` "
            "after viewing each figure (task T036).",
        ),
        (
            "Training split: rows and positives by type",
            md_table(
                ["type", "normal", "positive", "positive rate"],
                [
                    (t, int(r[0]), int(r[1]), float(r["positive_rate"]))
                    for t, r in per_type.iterrows()
                ],
            ),
        ),
        (
            "Flag features: positive rate by value (training split)",
            md_table(["flag", "value", "n", "positive rate"], flag_table.itertuples(index=False)),
        ),
    ]
    for path, title in figures:
        name = Path(path).name
        rel = Path(path).relative_to(reports) if Path(path).is_relative_to(reports) else Path(path)
        obs = notes.get(name, "")
        sections.append((title, f"![{title}]({rel})\n\nFigure: `{name}`\n\nObservation: {obs}"))
    return write_markdown(reports / "eda_summary.md", "EDA Summary", sections)


def figure_list(cfg: Config) -> list[str]:
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "eda"
    return sorted(str(p.name) for p in fig_dir.glob("eda_*.png"))


__all__ = ["run_eda", "figure_list", "write_summary", "json"]
