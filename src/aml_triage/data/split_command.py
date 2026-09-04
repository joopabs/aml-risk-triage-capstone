"""CLI handler: split."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_GUARD, EXIT_OK, EXIT_VALIDATION
from aml_triage.data.load import load_raw
from aml_triage.data.schema import SchemaError, load_schema
from aml_triage.data.split import SplitGuardError, make_split, write_split
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.split")


def run_split(args: argparse.Namespace, cfg: Config) -> int:
    cfg.require(["paths.raw_csv"])
    try:
        df = load_raw(cfg.paths.raw_csv, load_schema())
    except (SchemaError, FileNotFoundError) as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    try:
        parts, manifest = make_split(df, cfg)
        path = write_split(parts, manifest, cfg.paths.processed_dir)
    except SplitGuardError as exc:
        print(f"split guard: {exc}", file=sys.stderr)
        return EXIT_GUARD
    for name in ("train", "val", "test"):
        log.info("%s: rows=%d positives=%d steps=%s", name, manifest.rows[name], manifest.positives[name], manifest.step_ranges[name])
    print(f"wrote {path}")
    return EXIT_OK
