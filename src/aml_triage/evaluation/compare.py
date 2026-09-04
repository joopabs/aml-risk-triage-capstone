"""Comparison tables and curves across candidates and comparators (spec FR-053, research R-10)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

from aml_triage.config import Config
from aml_triage.data.split import load_split
from aml_triage.evaluation.calibration import reliability_table
from aml_triage.evaluation.capacity import capacity_suite
from aml_triage.evaluation.metrics import compute_metrics
from aml_triage.models.comparators import random_rank, rule_rank
from aml_triage.models.registry import COMPARATOR_IDS
from aml_triage.models.train import list_runs, load_run
from aml_triage.reporting.figures import apply_style, save_figure
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import write_json

NARRATIVE_FILENAME = "model_comparison_narrative.md"
COMPARATOR_LABELS = {
    "dummy": "dummy (chronological order)",
    "random_rank": "random ranking",
    "rule_rank": "rule comparator (flag, then amount)",
}


def comparator_runs(
    cfg: Config, split: str, template_preds: pd.DataFrame
) -> dict[str, dict[str, Any]]:
    """Score the split with the two training-free comparators using the same rows as the models."""
    raw = load_split(cfg.paths.processed_dir, split)[["row_index", "amount"]]
    meta = template_preds.drop(columns=["score"]).merge(raw, on="row_index", how="left")
    out = {}
    for cid in COMPARATOR_IDS:
        s = random_rank(meta, cfg.seed) if cid == "random_rank" else rule_rank(meta, meta["amount"])
        preds = meta.drop(columns=["amount"]).copy()
        preds["score"] = (
            s.to_numpy() / 2.0 if cid == "rule_rank" else s.to_numpy()
        )  # rule scores in [0,2) -> [0,1)
        m = compute_metrics(preds["isFraud"], preds["score"], 0.5, cfg.evaluation.degenerate_eps)
        cap = capacity_suite(
            preds[["row_index", "step", "isFraud", "score"]],
            cfg.review.k_grid,
            cfg.review.review_period_steps,
        )
        out[cid] = {
            "candidate_id": cid,
            "feature_set": "-",
            "split": split,
            "metrics": m,
            "recall_at_k": {k: v["recall_at_k"] for k, v in cap.items()},
            "precision_at_k": {k: v["precision_at_k"] for k, v in cap.items()},
            "preds": preds,
        }
    return out


def collect(cfg: Config, split: str) -> dict[str, dict[str, Any]]:
    runs: dict[str, dict[str, Any]] = {}
    template = None
    for rid in list_runs(cfg, split):
        metrics, preds = load_run(cfg, rid, split)
        metrics["preds"] = preds
        runs[rid] = metrics
        template = template if template is not None else preds
    if template is not None:
        runs.update(comparator_runs(cfg, split, template))
    return runs


def _label(r: dict[str, Any]) -> str:
    cid = r["candidate_id"]
    if cid in COMPARATOR_LABELS and r.get("feature_set", "-") in ("-", "primary"):
        return (
            COMPARATOR_LABELS[cid]
            if cid != "dummy"
            else f"{COMPARATOR_LABELS[cid]} [{r['feature_set']}]"
        )
    return f"{cid} [{r['feature_set']}]"


def build_tables(cfg: Config, runs: dict[str, dict[str, Any]]) -> dict[str, str]:
    K = str(cfg.review.primary_k)
    order = sorted(
        runs.values(),
        key=lambda r: (
            -(r["metrics"]["pr_auc"] if r["metrics"]["pr_auc"] == r["metrics"]["pr_auc"] else -1)
        ),
    )
    main_rows = [
        (
            _label(r),
            r["metrics"]["pr_auc"],
            r["metrics"]["roc_auc"],
            (r["recall_at_k"][K]["mean_over_periods"]),
            (r["recall_at_k"][K]["pooled"]),
            (r["precision_at_k"][K]["mean_over_periods"]),
            r["metrics"]["brier"],
            r["metrics"]["ece"],
            "yes" if r["metrics"]["degenerate_scores"] else "",
        )
        for r in order
    ]
    kgrid_rows = [
        (_label(r), *[r["recall_at_k"][str(k)]["mean_over_periods"] for k in cfg.review.k_grid])
        for r in order
    ]
    pgrid_rows = [
        (_label(r), *[r["precision_at_k"][str(k)]["mean_over_periods"] for k in cfg.review.k_grid])
        for r in order
    ]
    thr_rows = [
        (
            _label(r),
            r["metrics"]["threshold"],
            r["metrics"]["precision"],
            r["metrics"]["recall"],
            r["metrics"]["f1"],
            r["metrics"]["fpr"],
            r["metrics"]["confusion_matrix"]["tp"],
            r["metrics"]["confusion_matrix"]["fp"],
            r["metrics"]["confusion_matrix"]["fn"],
            r["metrics"]["confusion_matrix"]["tn"],
        )
        for r in order
    ]
    prev = next(iter(runs.values()))["metrics"]["prevalence"]
    acc_rows = [(_label(r), r["metrics"]["accuracy"], prev, 1 - prev) for r in order]
    return {
        "main": md_table(
            [
                "candidate [feature set]",
                "PR-AUC",
                "ROC-AUC",
                f"Recall@{K} (mean/period)",
                f"Recall@{K} (pooled)",
                f"Precision@{K} (mean/period)",
                "Brier",
                "ECE",
                "degenerate",
            ],
            main_rows,
        ),
        "kgrid": md_table(
            ["candidate [feature set]", *[f"Recall@{k}" for k in cfg.review.k_grid]], kgrid_rows
        ),
        "pgrid": md_table(
            ["candidate [feature set]", *[f"Precision@{k}" for k in cfg.review.k_grid]], pgrid_rows
        ),
        "threshold": md_table(
            [
                "candidate [feature set]",
                "threshold",
                "precision",
                "recall",
                "F1",
                "FPR",
                "TP",
                "FP",
                "FN",
                "TN",
            ],
            thr_rows,
        ),
        "accuracy": md_table(
            [
                "candidate [feature set]",
                "accuracy",
                "prevalence",
                "majority-class accuracy (1 - prevalence)",
            ],
            acc_rows,
        ),
    }


def draw_curves(cfg: Config, runs: dict[str, dict[str, Any]], split: str) -> list[str]:
    apply_style()
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "models"
    paths = []
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for _rid, r in runs.items():
        p = r["preds"]
        if r["metrics"]["degenerate_scores"]:
            continue
        prec, rec, _ = precision_recall_curve(p["isFraud"], p["score"])
        ax.plot(rec, prec, lw=1.2, label=f"{_label(r)} (AP={r['metrics']['pr_auc']:.3f})")
    ax.axhline(
        next(iter(runs.values()))["metrics"]["prevalence"],
        color="grey",
        ls="--",
        lw=1,
        label="prevalence (no-skill)",
    )
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_title(f"Precision-recall curves ({split} split)")
    ax.legend(fontsize=7)
    paths.append(
        str(
            save_figure(
                fig,
                fig_dir / f"pr_curves_{split}.png",
                "Degenerate (constant-score) candidates omitted; the dashed line is the no-skill PR-AUC (prevalence).",
            )
        )
    )
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for _rid, r in runs.items():
        p = r["preds"]
        if r["metrics"]["degenerate_scores"]:
            continue
        fpr, tpr, _ = roc_curve(p["isFraud"], p["score"])
        ax.plot(fpr, tpr, lw=1.2, label=f"{_label(r)} (AUC={r['metrics']['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], color="grey", ls="--", lw=1)
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.set_title(f"ROC curves ({split} split)")
    ax.legend(fontsize=7)
    paths.append(
        str(
            save_figure(
                fig,
                fig_dir / f"roc_curves_{split}.png",
                "ROC is reported as a secondary metric; PR-AUC is primary under 0.1-1% prevalence.",
            )
        )
    )
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for _rid, r in runs.items():
        if r["candidate_id"] in COMPARATOR_IDS or r["metrics"]["degenerate_scores"]:
            continue
        rows = [
            x for x in reliability_table(r["preds"]["isFraud"], r["preds"]["score"]) if x["n"] > 0
        ]
        ax.plot(
            [x["mean_score"] for x in rows],
            [x["observed_rate"] for x in rows],
            marker="o",
            ms=3,
            lw=1,
            label=f"{_label(r)} (Brier={r['metrics']['brier']:.4f})",
        )
    ax.plot([0, 1], [0, 1], color="grey", ls="--", lw=1)
    ax.set_xlabel("mean predicted score")
    ax.set_ylabel("observed positive rate")
    ax.set_title(f"Reliability curves ({split} split, 10 bins)")
    ax.legend(fontsize=7)
    paths.append(
        str(
            save_figure(
                fig,
                fig_dir / f"calibration_curves_{split}.png",
                "Class-weighted models are expected to over-predict; calibration is assessed on validation before any correction (research R-09).",
            )
        )
    )
    return paths


def render_report(cfg: Config) -> Path:
    reports = Path(cfg.paths.reports_dir)
    sections: list[tuple[str, str]] = [
        (
            "Method",
            f"Every candidate is trained on the training split of its feature set and scored on the split named in "
            f"each section; comparators need no training. Review period = {cfg.review.review_period_steps} steps; "
            f"primary K = {cfg.review.primary_k}; k_grid = {cfg.review.k_grid}. Threshold metrics use 0.5 until the "
            f"operating point is chosen on validation (Milestone 6). Accuracy appears last, next to the majority-class "
            f"baseline, and is never a selection criterion (FR-007). PR-AUC is primary; the no-skill PR-AUC equals prevalence.",
        )
    ]
    for split in ("val", "test"):
        js = reports / f"model_comparison_{split}.json"
        if not js.exists():
            continue
        data = json.loads(js.read_text(encoding="utf-8"))
        t = data["tables"]
        title = "Validation" if split == "val" else "Test (single-touch evaluation)"
        sections += [
            (f"{title}: headline metrics", t["main"]),
            (f"{title}: Recall@K across the capacity grid (mean over review periods)", t["kgrid"]),
            (
                f"{title}: Precision@K across the capacity grid (mean over review periods)",
                t["pgrid"],
            ),
            (f"{title}: threshold metrics at {data['threshold']}", t["threshold"]),
            (f"{title}: accuracy (reported last, with prevalence)", t["accuracy"]),
            (
                f"{title}: curves",
                "\n\n".join(
                    f"![{Path(p).stem}]({Path(p).relative_to(reports)})" for p in data["figures"]
                ),
            ),
        ]
    sections += narrative_sections(
        reports / NARRATIVE_FILENAME,
        "<!-- Task T050/T059: write reports/model_comparison_narrative.md after reviewing the tables above. -->\n\n_Pending review._",
    )
    return write_markdown(reports / "model_comparison.md", "Model Comparison", sections)


def compare(cfg: Config, split: str) -> Path:
    runs = collect(cfg, split)
    if not runs:
        raise FileNotFoundError(
            f"no runs with {split} predictions under {Path(cfg.paths.models_dir) / 'runs'}"
        )
    tables = build_tables(cfg, runs)
    figures = draw_curves(cfg, runs, split)
    summary = {
        "split": split,
        "threshold": 0.5,
        "primary_k": cfg.review.primary_k,
        "k_grid": cfg.review.k_grid,
        "runs": {rid: {k: v for k, v in r.items() if k != "preds"} for rid, r in runs.items()},
        "tables": tables,
        "figures": figures,
        "config_hash": cfg.config_hash(),
    }
    write_json(summary, Path(cfg.paths.reports_dir) / f"model_comparison_{split}.json")
    return render_report(cfg)


__all__ = ["compare", "collect", "render_report", "np"]
