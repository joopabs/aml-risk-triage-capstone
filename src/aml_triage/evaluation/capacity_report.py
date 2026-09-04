"""Capacity analysis report for the selected run (spec FR-005/FR-006, task T059).

Tables are generated from saved run metrics; the human narrative lives in
reports/capacity_analysis_narrative.md and is merged on render. All business figures are
illustrative counts, never currency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from aml_triage.config import Config
from aml_triage.evaluation.compare import COMPARATOR_LABELS, collect
from aml_triage.reporting.figures import PALETTE, apply_style, save_figure
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import write_json

NARRATIVE_FILENAME = "capacity_analysis_narrative.md"


def _mean_hits(r: dict[str, Any]) -> float:
    pp = r.get("per_period") or []
    return sum(p["hits"] for p in pp) / len(pp) if pp else float("nan")


def capacity_report(cfg: Config, selected_run: str) -> Path:
    apply_style()
    reports = Path(cfg.paths.reports_dir)
    K = cfg.review.primary_k
    grid = cfg.review.k_grid
    out: dict[str, Any] = {
        "selected_run": selected_run,
        "primary_k": K,
        "k_grid": grid,
        "splits": {},
    }
    sections: list[tuple[str, str]] = [
        (
            "Scope",
            f"Selected run `{selected_run}`; review period = {cfg.review.review_period_steps} steps (one simulated day); "
            f"capacity K = {K} with sensitivity grid {grid}. Recall@K = share of a period's positives inside the top-K; "
            f"Precision@K = share of the top-K that are positives. Business figures are **illustrative counts** on synthetic data.",
        )
    ]
    fig_paths = []
    for split in ("val", "test"):
        runs = collect(cfg, split)
        if selected_run not in runs:
            continue
        sel = runs[selected_run]
        # Recall/precision vs K
        rows = [
            (
                k,
                sel["recall_at_k"][str(k)]["mean_over_periods"],
                sel["recall_at_k"][str(k)]["pooled"],
                sel["precision_at_k"][str(k)]["mean_over_periods"],
                sel["precision_at_k"][str(k)]["pooled"],
            )
            for k in grid
        ]
        sections.append(
            (
                f"{split}: Recall@K and Precision@K across the capacity grid",
                md_table(
                    [
                        "K",
                        "Recall@K mean/period",
                        "Recall@K pooled",
                        "Precision@K mean/period",
                        "Precision@K pooled",
                    ],
                    rows,
                ),
            )
        )
        # per-period at primary K
        pp = sel["per_period"]
        prow = [
            (
                p["period_index"] + 1,
                f"{p['step_range'][0]}–{p['step_range'][1]}",
                p["n_rows"],
                p["n_positives"],
                p["k_effective"],
                p["hits"],
                p["n_positives"] - p["hits"],
                p["k_effective"] - p["hits"],
                p["recall_at_k"],
                p["precision_at_k"],
            )
            for p in pp
        ]
        sections.append(
            (
                f"{split}: per review period at K = {K}",
                md_table(
                    [
                        "day",
                        "steps",
                        "transactions",
                        "positives",
                        "reviewed (k_eff)",
                        "positives caught",
                        "positives missed (FN)",
                        "reviews spent on normals (FP)",
                        "Recall@K",
                        "Precision@K",
                    ],
                    prow,
                ),
            )
        )
        # illustrative KPI vs comparators (mean positives surfaced per period at K)
        kpi_rows = []
        sel_hits = _mean_hits(sel)
        for rid in [
            selected_run,
            "rule_rank",
            "random_rank",
            *[r for r in runs if r.startswith("dummy__")][:1],
        ]:
            r = runs.get(rid)
            if not r:
                continue
            h = _mean_hits(r) if r.get("per_period") else None
            if (
                h is None
            ):  # comparators carry recall/precision but not per_period; derive from precision@K
                prec = r["precision_at_k"][str(K)]["mean_over_periods"]
                h = prec * K if prec is not None else float("nan")
            label = (
                COMPARATOR_LABELS.get(r["candidate_id"], r["candidate_id"])
                if rid != selected_run
                else f"{sel['candidate_id']} [{sel['feature_set']}] (selected)"
            )
            kpi_rows.append(
                (
                    label,
                    round(h, 1),
                    round(sel_hits / h, 1) if h else "n/a",
                    r["recall_at_k"][str(K)]["mean_over_periods"],
                )
            )
        sections.append(
            (
                f"{split}: illustrative KPI — positives surfaced per review period at K = {K}",
                md_table(
                    [
                        "ranking",
                        "illustrative positives surfaced per day",
                        "improvement factor vs selected",
                        f"Recall@{K}",
                    ],
                    kpi_rows,
                )
                + "\n\n_Illustrative counts on synthetic data; not a real-world estimate and never expressed in currency._",
            )
        )
        out["splits"][split] = {"grid": rows, "per_period": pp, "kpi": kpi_rows}
        # figure
        fig, ax1 = plt.subplots(figsize=(7.5, 4.2))
        ks = grid
        ax1.plot(
            ks,
            [sel["recall_at_k"][str(k)]["mean_over_periods"] for k in ks],
            marker="o",
            color=PALETTE["positive"],
            label="Recall@K (mean/period)",
        )
        ax1.plot(
            ks,
            [sel["precision_at_k"][str(k)]["mean_over_periods"] for k in ks],
            marker="s",
            color=PALETTE["normal"],
            label="Precision@K (mean/period)",
        )
        med_pos = sorted(p["n_positives"] for p in pp)[len(pp) // 2]
        ax1.axvline(
            med_pos, color="grey", ls="--", lw=1, label=f"median positives/period = {med_pos}"
        )
        ax1.axvline(K, color="black", ls=":", lw=1, label=f"primary K = {K}")
        ax1.set_xlabel("K (reviews per period)")
        ax1.set_ylabel("rate")
        ax1.set_ylim(0, 1.05)
        ax1.legend(fontsize=8)
        ax1.set_title(f"Recall and precision at capacity K ({split} split, {selected_run})")
        fig_paths.append(
            str(
                save_figure(
                    fig,
                    reports / "figures" / "models" / f"capacity_curve_{split}.png",
                    "Recall rises with K until K exceeds the positives in a period; precision falls once K passes that point.",
                )
            )
        )
    if fig_paths:
        sections.append(
            (
                "Figures",
                "\n\n".join(
                    f"![{Path(p).stem}]({Path(p).relative_to(reports)})" for p in fig_paths
                ),
            )
        )
    sections += narrative_sections(
        reports / NARRATIVE_FILENAME,
        "<!-- Task T059: write reports/capacity_analysis_narrative.md after reviewing the tables above. -->\n\n_Pending review._",
    )
    write_json(out, reports / "capacity_analysis.json")
    return write_markdown(reports / "capacity_analysis.md", "Capacity Analysis", sections)
