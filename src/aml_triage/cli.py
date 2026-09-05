"""Command-line entry point: ``python -m aml_triage <command> [--config PATH] [--seed INT]``.

Every command listed in contracts/cli-contract.md is registered here. In Milestone 1 they are
stubs that exit 1 with a clear message; later milestones replace the handlers.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from pydantic import ValidationError

from aml_triage import __version__
from aml_triage.config import Config, load
from aml_triage.constants import (
    DISCLAIMER,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_VALIDATION,
)
from aml_triage.utils.logging import get_logger
from aml_triage.utils.seed import set_global_seed

log = get_logger("aml_triage.cli")

# (name, help, milestone that implements it)
COMMANDS: list[tuple[str, str, str]] = [
    ("fetch-data", "Download the dataset and verify its checksum", "M2"),
    ("validate-schema", "Validate raw data against configs/schema.yaml", "M2"),
    ("profile", "Write the data quality report", "M2"),
    ("data-dictionary", "Write the data dictionary", "M2"),
    ("split", "Create the temporal train/val/test split", "M3"),
    ("build-features", "Build feature matrices for a feature set", "M3"),
    ("eda", "Write EDA figures and summary skeleton", "M3"),
    ("select-features", "Run feature selection on training data", "M4"),
    ("pca", "Run PCA analysis on training data", "M4"),
    ("train", "Train candidates and score a split", "M5"),
    ("compare", "Write comparison tables and curves", "M5"),
    ("tune", "Hyperparameter search on a training subsample", "M6"),
    ("choose-operating-point", "Choose threshold and priority rule on validation", "M6"),
    ("freeze", "Freeze the operating point and unlock a single test evaluation", "M6"),
    ("evaluate", "Evaluate all candidates on a split (test: once)", "M6"),
    ("select", "Build the selection matrix and persist the model bundle", "M6"),
    ("reproduce-check", "Refit twice and record the reproducibility tolerance", "M6"),
    ("explain", "SHAP global/local explanations and PDP/ICE", "M7"),
    ("fairness-availability", "Record sensitive-attribute availability", "M7"),
    ("fairness", "Write the Bias & Fairness Analysis", "M7"),
    ("build-report", "Assemble the final report from section files", "M8"),
    ("queue", "Write the top-K review queue for a period", "M6"),
]

Handler = Callable[[argparse.Namespace, Config], int]


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="configs/base.yaml", help="path to a run config")
    parser.add_argument("--seed", type=int, default=None, help="override config seed")


def _add_command_options(name: str, parser: argparse.ArgumentParser) -> None:
    """Command-specific options from contracts/cli-contract.md (independent conditions)."""
    if name == "build-features":
        parser.add_argument("--feature-set", required=True)
    if name in {"select-features", "train"}:
        parser.add_argument("--feature-set", default=None)
    if name in {"train", "compare", "evaluate"}:
        parser.add_argument("--split", choices=["val", "test"], default="val")
    if name in {"train", "tune"}:
        parser.add_argument("--models", default="dummy,logreg,balanced_rf,hgb")
    if name == "evaluate":
        parser.add_argument("--force-reevaluate", action="store_true")
        parser.add_argument("--reason", default=None)
    if name == "explain":
        parser.add_argument("--model", default="LATEST")
    if name == "queue":
        parser.add_argument("--period", type=int, required=True)
    if name == "fetch-data":
        parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aml_triage",
        description="Explainable AML transaction-risk triage pipeline (educational, synthetic data).",
        epilog=DISCLAIMER,
    )
    parser.add_argument("--version", action="version", version=f"aml_triage {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for name, help_text, milestone in COMMANDS:
        p = sub.add_parser(name, help=f"{help_text} [{milestone}]")
        _add_common(p)
        _add_command_options(name, p)
        p.set_defaults(handler=_resolve_handler(name), milestone=milestone)
    return parser


def _resolve_handler(name: str) -> Handler:
    """Return the implemented handler for ``name`` or the not-implemented stub."""
    from aml_triage.data.commands import HANDLERS as data_handlers
    from aml_triage.data.split_command import run_split
    from aml_triage.eda.commands import run_eda_cmd
    from aml_triage.explain.commands import run_explain
    from aml_triage.fairness.commands import run_fairness, run_fairness_availability
    from aml_triage.features.commands import run_build_features
    from aml_triage.features.selection_commands import run_pca_cmd, run_select_features
    from aml_triage.models.commands import run_compare, run_train
    from aml_triage.models.lifecycle_commands import HANDLERS as lifecycle_handlers
    from aml_triage.reporting.commands import run_build_report

    registry: dict[str, Handler] = {
        **data_handlers,
        "split": run_split,
        "build-features": run_build_features,
        "eda": run_eda_cmd,
        "select-features": run_select_features,
        "pca": run_pca_cmd,
        "train": run_train,
        "compare": run_compare,
        **lifecycle_handlers,
        "explain": run_explain,
        "fairness-availability": run_fairness_availability,
        "fairness": run_fairness,
        "build-report": run_build_report,
    }
    return registry.get(name, _not_implemented)


def _not_implemented(args: argparse.Namespace, cfg: Config) -> int:
    print(
        f"aml_triage {args.command}: not implemented yet (planned for Milestone {args.milestone}).",
        file=sys.stderr,
    )
    return EXIT_ERROR


def _load_config(args: argparse.Namespace) -> Config:
    overrides = {"seed": args.seed} if args.seed is not None else None
    return load(args.config, overrides=overrides)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK
    try:
        cfg = _load_config(args)
    except SystemExit as exc:  # config.load exits 2 on missing file
        return exc.code if isinstance(exc.code, int) else EXIT_VALIDATION
    except (ValidationError, ValueError, OSError):
        return EXIT_VALIDATION
    set_global_seed(cfg.seed)
    log.info(
        "command=%s config=%s hash=%s seed=%d",
        args.command,
        args.config,
        cfg.config_hash(),
        cfg.seed,
    )
    log.info("disclaimer: %s", DISCLAIMER)
    handler: Handler = args.handler
    return handler(args, cfg)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
