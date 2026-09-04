"""CLI handler: eda."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_OK
from aml_triage.eda.plots import run_eda
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.eda")


def run_eda_cmd(args: argparse.Namespace, cfg: Config) -> int:
    try:
        summary, figures = run_eda(cfg)
    except FileNotFoundError as exc:
        print(
            f"missing prerequisite: {exc} (run `split` and `build-features --feature-set primary` first)",
            file=sys.stderr,
        )
        return EXIT_MISSING_PREREQ
    log.info("wrote %d figures and %s", len(figures), summary)
    print(f"wrote {summary} and {len(figures)} figures")
    return EXIT_OK
