"""CLI handler: explain."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aml_triage.config import Config
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_OK
from aml_triage.explain.captions import feature_rationale
from aml_triage.explain.pdp_ice import run_pdp_ice
from aml_triage.explain.shap_reports import load_bundle, run_shap
from aml_triage.features.base import load_registry
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import write_json
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.explain")
NARRATIVE_FILENAME = "explainability_narrative.md"


def run_explain(args: argparse.Namespace, cfg: Config) -> int:
    try:
        bundle, version = load_bundle(cfg, args.model)
    except FileNotFoundError as exc:
        print(f"missing prerequisite: {exc} (run `select` first)", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    shap_out = run_shap(cfg, args.model)
    X_eval, _ = shap_out.pop("eval_sample").values()
    from aml_triage.features.pipeline import load_feature_matrix

    _, meta_test = load_feature_matrix(cfg.paths.processed_dir, bundle["feature_set"], "test")
    y_eval = meta_test.iloc[X_eval.index]["isFraud"].astype(int)
    top = list(shap_out["global_mean_abs_shap"])[: cfg.explain.pdp_top_features]
    pdp_out = run_pdp_ice(cfg, bundle["estimator"], X_eval, y_eval, top, version)
    defs = load_registry(cfg.features.registry)

    reports = Path(cfg.paths.reports_dir)
    rel = lambda p: Path(p).relative_to(reports)  # noqa: E731
    glob_rows = [
        (f, v, feature_rationale(defs, f))
        for f, v in list(shap_out["global_mean_abs_shap"].items())[:15]
    ]
    sections = [
        (
            "Scope",
            f"Released bundle `{version}` (`{shap_out['candidate_id']}` on `{shap_out['feature_set']}`). Explainer: {shap_out['explainer']}, contributions in {shap_out['units']}. Background: {shap_out['background_rows']:,} seeded training rows; global sample: {shap_out['eval_rows']:,} seeded test rows; local examples: the top-ranked transactions of the first test review period. Explanations describe the model, not the transactions' true nature.",
        ),
        (
            "Global",
            md_table(
                ["feature", f"mean |SHAP| ({shap_out['units']})", "registry rationale"], glob_rows
            )
            + "\n\n"
            + "\n\n".join(f"![{Path(p).stem}]({rel(p)})" for p in shap_out["global_figures"]),
        ),
        (
            "Local Examples",
            "\n\n".join(
                f"**Rank {e['rank']}** (row {e['row_index']:,}, step {e['step']}, {e['type']}, score {e['score']:.4f})\n\n![{Path(e['figure']).stem}]({rel(e['figure'])})\n\n{e['caption']}"
                for e in shap_out["local_examples"]
            ),
        ),
        (
            "PDP/ICE Validity",
            md_table(
                ["feature", "status", "reason", "alternative"],
                [
                    (c["feature"], c["status"], c["reason"], c["alternative"] or "")
                    for c in pdp_out["validity"]
                ],
            )
            + "\n\n"
            + "\n\n".join(f"![{Path(p).stem}]({rel(p)})" for p in pdp_out["figures"]),
        ),
        (
            "Permutation importance (alternative / cross-check)",
            md_table(
                ["feature", "mean drop in PR-AUC", "std"],
                [
                    (r["feature"], r["mean_drop_in_pr_auc"], r["std"])
                    for r in pdp_out["permutation_importance"][:15]
                ],
            ),
        ),
    ]
    sections += narrative_sections(
        reports / NARRATIVE_FILENAME,
        "<!-- Task T071: write reports/explainability_narrative.md after reviewing the figures and tables above. -->\n\n_Pending review (task T071)._",
    )
    out = write_markdown(reports / "explainability.md", "Explainability", sections)
    write_json({**shap_out, "pdp_ice": pdp_out}, reports / "explainability.json")
    log.info(
        "wrote %s (%d global figures, %d local, %d pdp figures)",
        out,
        len(shap_out["global_figures"]),
        len(shap_out["local_examples"]),
        len(pdp_out["figures"]),
    )
    print(f"wrote {out}")
    return EXIT_OK
