"""CLI handlers: fairness-availability, fairness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aml_triage.config import Config
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_OK
from aml_triage.evaluation.threshold import apply_operating_point, load_operating_point
from aml_triage.fairness.availability import availability_record
from aml_triage.fairness.report import render
from aml_triage.fairness.slices import slice_analysis
from aml_triage.utils.io import read_json
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.fairness")


def run_fairness_availability(args: argparse.Namespace, cfg: Config) -> int:
    cfg.require(["paths.raw_csv"])
    rec = availability_record(cfg)
    log.info(
        "any_valid_label=%s; proxy columns=%s", rec["any_valid_label"], rec["proxy_scan_columns"]
    )
    print(
        f"wrote {cfg.paths.reports_dir}/fairness_availability.json (any_valid_label={rec['any_valid_label']})"
    )
    return EXIT_OK


def run_fairness(args: argparse.Namespace, cfg: Config) -> int:
    reports = Path(cfg.paths.reports_dir)
    avail_path = reports / "fairness_availability.json"
    if not avail_path.exists():
        print("missing prerequisite: run `fairness-availability` first", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    op = load_operating_point(cfg)
    if op is None:
        print("missing prerequisite: operating point not found", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    from aml_triage.models.train import load_run

    try:
        _, preds = load_run(cfg, op["selected_run"], "test")
    except FileNotFoundError:
        print(
            "missing prerequisite: test predictions of the selected run (run `evaluate --split test`)",
            file=sys.stderr,
        )
        return EXIT_MISSING_PREREQ
    availability = read_json(avail_path)
    slices = slice_analysis(cfg, apply_operating_point(op, preds), op)
    demographic = (
        None  # computed only if valid labels exist; PaySim has none (see availability record)
    )
    if availability["any_valid_label"]:
        print(
            "valid sensitive-group labels were found; demographic metrics require a group column mapping (not implemented for this dataset)",
            file=sys.stderr,
        )
    out = render(cfg, availability, slices, demographic)
    print(f"wrote {out}")
    return EXIT_OK
