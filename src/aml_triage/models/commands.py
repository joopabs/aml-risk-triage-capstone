"""CLI handlers: train, compare."""

from __future__ import annotations

import argparse
import sys

from aml_triage.config import Config
from aml_triage.constants import EXIT_GUARD, EXIT_MISSING_PREREQ, EXIT_OK
from aml_triage.evaluation.compare import compare
from aml_triage.features.pipeline import LeakageError
from aml_triage.models.train import TestAccessError, train_and_score
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.models")


def run_train(args: argparse.Namespace, cfg: Config) -> int:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    feature_set = getattr(args, "feature_set", None) or cfg.features.default_set
    for mid in models:
        try:
            res = train_and_score(cfg, mid, feature_set, args.split, context="train")
        except TestAccessError as exc:
            print(f"test access guard: {exc}", file=sys.stderr)
            return EXIT_GUARD
        except LeakageError as exc:
            print(f"leakage guard: {exc}", file=sys.stderr)
            return EXIT_GUARD
        except FileNotFoundError as exc:
            print(f"missing prerequisite: {exc}", file=sys.stderr)
            return EXIT_MISSING_PREREQ
        m = res["metrics"]
        K = str(cfg.review.primary_k)
        log.info(
            "%s [%s] %s: PR-AUC=%.4f ROC-AUC=%.4f Recall@%s=%.3f fit=%.1fs%s",
            mid, feature_set, args.split, m["pr_auc"], m["roc_auc"], K,
            res["recall_at_k"][K]["mean_over_periods"] or 0.0, res["fit_seconds"],
            " DEGENERATE" if m["degenerate_scores"] else "",
        )
    print(f"trained {len(models)} candidate(s) on [{feature_set}], scored {args.split}")
    return EXIT_OK


def run_compare(args: argparse.Namespace, cfg: Config) -> int:
    try:
        out = compare(cfg, args.split)
    except FileNotFoundError as exc:
        print(f"missing prerequisite: {exc} (run `train` first)", file=sys.stderr)
        return EXIT_MISSING_PREREQ
    print(f"wrote {out}")
    return EXIT_OK
