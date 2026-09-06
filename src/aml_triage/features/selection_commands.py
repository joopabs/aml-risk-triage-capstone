"""CLI handlers: select-features, pca."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_GUARD, EXIT_MISSING_PREREQ, EXIT_OK, EXIT_VALIDATION
from aml_triage.features.pca import run_pca
from aml_triage.features.pipeline import LeakageError
from aml_triage.features.selection import render_report, run_selection, update_registry_selected
from aml_triage.isolation import guard_tracked_write
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.selection")


def run_select_features(args: argparse.Namespace, cfg: Config) -> int:
    try:
        guard_tracked_write(cfg, cfg.features.registry, "configs/features.yaml", "feature registry")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    try:
        result = run_selection(cfg, getattr(args, "feature_set", None) or cfg.features.default_set)
    except FileNotFoundError as exc:
        print(
            f"missing prerequisite: {exc} (run `build-features --feature-set primary` first)",
            file=sys.stderr,
        )
        return EXIT_MISSING_PREREQ
    except LeakageError as exc:
        print(f"leakage guard: {exc}", file=sys.stderr)
        return EXIT_GUARD
    report = render_report(result, cfg.paths.reports_dir)
    update_registry_selected(cfg.features.registry, result["selected_registry_features"])
    log.info(
        "selected %d of %d columns (%s)",
        len(result["selected_columns"]),
        len(result["before"]),
        result["rule_applied"],
    )
    print(f"wrote {report}\nupdated {cfg.features.registry} (`selected` set)")
    return EXIT_OK


def run_pca_cmd(args: argparse.Namespace, cfg: Config) -> int:
    try:
        result = run_pca(cfg, cfg.features.default_set)
    except FileNotFoundError as exc:
        print(
            f"missing prerequisite: {exc} (run `build-features --feature-set primary` first)",
            file=sys.stderr,
        )
        return EXIT_MISSING_PREREQ
    except LeakageError as exc:
        print(f"leakage guard: {exc}", file=sys.stderr)
        return EXIT_GUARD
    log.info("%d components for %s target", result["n_components"], result["n_components_target"])
    print(f"wrote {cfg.paths.reports_dir}/pca_report.md and pca_variant matrices")
    return EXIT_OK
