"""CLI handler: build-features."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_GUARD, EXIT_MISSING_PREREQ, EXIT_OK, EXIT_VALIDATION
from aml_triage.features.base import RegistryError
from aml_triage.features.pipeline import LeakageError, build_feature_matrices
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.features")


def run_build_features(args: argparse.Namespace, cfg: Config) -> int:
    try:
        outputs = build_feature_matrices(cfg, args.feature_set)
    except FileNotFoundError as exc:
        print(f"missing prerequisite: {exc} (run `split` first)", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    except RegistryError as exc:
        print(f"feature registry error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except LeakageError as exc:
        print(f"leakage guard: {exc}", file=sys.stderr)
        return EXIT_GUARD
    for name, path in outputs.items():
        log.info("%s -> %s", name, path)
    print("\n".join(f"wrote {p}" for p in outputs.values()))
    return EXIT_OK
