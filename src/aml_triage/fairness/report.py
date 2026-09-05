"""Bias & Fairness Analysis report (spec FR-070..FR-076; contracts/artifacts-contract.md headings)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from aml_triage.config import Config
from aml_triage.reporting.figures import PALETTE, apply_style, save_figure
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import write_json

NARRATIVE_FILENAME = "bias_fairness_narrative.md"
NON_MEASURABLE = "Demographic fairness metrics cannot be computed on this dataset because no valid sensitive-group labels exist."
HEADINGS = [
    "Sensitive-Attribute Availability Record",
    "Demographic Fairness",
    "Operational Error-Slice Analysis",
    "Limitations",
    "Mitigations",
    "Governance-Controlled Fairness Audit Plan",
]


def slice_figures(cfg: Config, slices: dict[str, Any]) -> list[str]:
    apply_style()
    fig_dir = Path(cfg.paths.reports_dir) / "figures" / "fairness"
    paths = []
    for dim, rows in slices["results"].items():
        fig, ax1 = plt.subplots(figsize=(8.5, 4))
        labels = [r["slice"] for r in rows]
        ax1.bar(labels, [r["n"] for r in rows], color=PALETTE["normal"], alpha=0.5, label="rows")
        ax1.set_yscale("log")
        ax1.set_ylabel("rows (log)")
        ax1.tick_params(axis="x", rotation=30)
        ax2 = ax1.twinx()
        ax2.plot(
            labels,
            [r["recall_at_k"] if r["recall_at_k"] is not None else float("nan") for r in rows],
            marker="o",
            color=PALETTE["positive"],
            label=f"Recall@{slices['primary_k']}",
        )
        ax2.plot(
            labels,
            [
                r["fnr_at_threshold"] if r["fnr_at_threshold"] is not None else float("nan")
                for r in rows
            ],
            marker="s",
            color="#8172B2",
            label="FNR at threshold",
        )
        ax2.set_ylim(0, 1.05)
        ax2.set_ylabel("rate")
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
        ax1.set_title(f"{slices['label']}: {dim} (test split)")
        paths.append(
            str(
                save_figure(
                    fig,
                    fig_dir / f"slice_{dim}.png",
                    f"Operational slice by {dim}; slices without positives show no recall point. This is an error-slice view, not a protected-group fairness measure.",
                )
            )
        )
    return paths


def render(
    cfg: Config,
    availability: dict[str, Any],
    slices: dict[str, Any],
    demographic: dict[str, Any] | None,
) -> Path:
    reports = Path(cfg.paths.reports_dir)
    figs = slice_figures(cfg, slices)
    rel = lambda p: Path(p).relative_to(reports)  # noqa: E731
    avail_rows = [
        (a, "yes" if v["present"] else "no", v["evidence"])
        for a, v in availability["per_attribute"].items()
    ]
    sections: list[tuple[str, str]] = [
        (
            HEADINGS[0],
            f"Checked on {availability['decided_on']} against the actual raw columns of `{Path(availability['source']).name}`: {', '.join(f'`{c}`' for c in availability['raw_columns'])}. Proxy scan terms: {', '.join(availability['proxy_scan_names'])}; matching columns: {availability['proxy_scan_columns'] or 'none'}.\n\n"
            + md_table(["attribute", "valid label present", "evidence"], avail_rows)
            + f"\n\n**any_valid_label = {str(availability['any_valid_label']).lower()}**",
        ),
    ]
    if availability["any_valid_label"] and demographic:
        per = demographic["per_group"]
        sections.append(
            (
                HEADINGS[1],
                md_table(
                    ["group", "n", "selection rate", "TPR", "FPR"],
                    [(g, v["n"], v["selection_rate"], v["tpr"], v["fpr"]) for g, v in per.items()],
                )
                + f"\n\nDemographic parity difference {demographic['demographic_parity_difference']:.4f}; equalized odds difference {demographic['equalized_odds_difference']:.4f}; disparate impact ratio {demographic['disparate_impact_ratio']:.4f}.",
            )
        )
    else:
        sections.append(
            (
                HEADINGS[1],
                NON_MEASURABLE
                + " What follows is an operational error-slice analysis over non-protected partitions of the data; it is not a fairness measurement across protected groups and must not be described as one.",
            )
        )
    slice_md = []
    for dim, rows in slices["results"].items():
        slice_md.append(
            f"**By {dim}**\n\n"
            + md_table(
                [
                    "slice",
                    "rows",
                    "positives",
                    "prevalence",
                    f"Recall@{slices['primary_k']}",
                    f"Precision@{slices['primary_k']}",
                    "FNR at threshold",
                    "FPR at threshold",
                    "Brier (calibrated)",
                ],
                [
                    (
                        r["slice"],
                        r["n"],
                        r["positives"],
                        r["prevalence"],
                        r["recall_at_k"],
                        r["precision_at_k"],
                        r["fnr_at_threshold"],
                        r["fpr_at_threshold"],
                        r["brier_calibrated"],
                    )
                    for r in rows
                ],
            )
        )
    sections.append(
        (
            HEADINGS[2],
            f"Label: **{slices['label']}**. Test split; K = {slices['primary_k']}; raw-score threshold {slices['threshold']}; amount and origin-balance band edges fitted on the training split ({slices['band_edges']}). Recall@K within a slice is the share of that slice's positives that fall inside their review period's top-K.\n\n"
            + "\n\n".join(slice_md)
            + "\n\n"
            + "\n\n".join(f"![{Path(p).stem}]({rel(p)})" for p in figs),
        )
    )
    narrative = dict(narrative_sections(reports / NARRATIVE_FILENAME, ""))
    if narrative.get(HEADINGS[2]):  # human observations appended to the generated slice tables
        title, body = sections[-1]
        sections[-1] = (
            title,
            body + "\n\n**Observations (task T078)**\n\n" + narrative[HEADINGS[2]],
        )
    for h in HEADINGS[3:]:
        sections.append(
            (
                h,
                narrative.get(h)
                or f"<!-- Task T078: write the '{h}' section in reports/{NARRATIVE_FILENAME}. -->\n\n_Pending review (task T078)._",
            )
        )
    write_json(
        {
            "availability": availability,
            "slices": slices,
            "demographic": demographic,
            "figures": figs,
        },
        reports / "bias_fairness_analysis.json",
    )
    return write_markdown(
        reports / "bias_fairness_analysis.md", "Bias & Fairness Analysis", sections
    )
