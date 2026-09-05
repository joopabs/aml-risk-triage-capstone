"""CLI handler: build-report."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_OK
from aml_triage.reporting.report_builder import MissingSectionError, build_report


def run_build_report(args: argparse.Namespace, cfg: Config) -> int:
    try:
        out = build_report(cfg)
    except MissingSectionError as exc:
        print(f"missing prerequisite: {exc}", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    print(f"wrote {out}")
    return EXIT_OK
