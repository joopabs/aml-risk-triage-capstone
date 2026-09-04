"""CLI handlers for Milestone 2 commands: fetch-data, validate-schema, profile, data-dictionary."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from aml_triage.config import Config
from aml_triage.constants import EXIT_MISSING_PREREQ, EXIT_OK, EXIT_VALIDATION
from aml_triage.data.dictionary import DictionaryError, build_dictionary
from aml_triage.data.load import load_raw
from aml_triage.data.profiling import run_profile
from aml_triage.data.schema import SchemaError, load_schema, validate_frame
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.data")


def run_fetch_data(args: argparse.Namespace, cfg: Config) -> int:
    script = Path("scripts/fetch_data.sh")
    if not script.exists():
        print("scripts/fetch_data.sh not found", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    cmd = [str(script)] + (["--dry-run"] if getattr(args, "dry_run", False) else [])
    return subprocess.run(cmd, check=False).returncode


def run_validate_schema(args: argparse.Namespace, cfg: Config) -> int:
    cfg.require(["paths.raw_csv"])
    schema = load_schema()
    try:
        df = load_raw(cfg.paths.raw_csv, schema)
    except (SchemaError, FileNotFoundError) as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    report = validate_frame(df, schema)
    print(report.summary())
    if not report.ok:
        print("schema validation FAILED", file=sys.stderr)
        return EXIT_VALIDATION
    print("schema validation OK")
    return EXIT_OK


def run_profile_cmd(args: argparse.Namespace, cfg: Config) -> int:
    cfg.require(["paths.raw_csv"])
    schema = load_schema()
    try:
        df = load_raw(cfg.paths.raw_csv, schema)
    except (SchemaError, FileNotFoundError) as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    md, js = run_profile(df, schema, cfg.paths.reports_dir, cfg.paths.raw_csv)
    log.info("wrote %s and %s", md, js)
    print(f"wrote {md}\nwrote {js}")
    return EXIT_OK


def run_data_dictionary(args: argparse.Namespace, cfg: Config) -> int:
    schema = load_schema()
    reports = Path(cfg.paths.reports_dir)
    try:
        out = build_dictionary(
            schema,
            reports / "data_dictionary.md",
            registry_path=cfg.features.registry,
            profile_path=reports / "data_quality.json",
        )
    except DictionaryError as exc:
        print(f"data dictionary error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    print(f"wrote {out}")
    return EXIT_OK


HANDLERS = {
    "fetch-data": run_fetch_data,
    "validate-schema": run_validate_schema,
    "profile": run_profile_cmd,
    "data-dictionary": run_data_dictionary,
}
