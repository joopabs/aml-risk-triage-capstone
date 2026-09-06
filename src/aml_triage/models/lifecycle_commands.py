"""CLI handlers: tune, choose-operating-point, freeze, evaluate, select, queue."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aml_triage.config import Config
from aml_triage.constants import EXIT_GUARD, EXIT_MISSING_PREREQ, EXIT_OK, EXIT_VALIDATION
from aml_triage.evaluation.threshold import DEFAULT_PROCESSED_DIR, choose_operating_point
from aml_triage.models.lifecycle import PrerequisiteError, evaluate_test, freeze, render_reproducibility_readme, reproduce_check, select, write_queue
from aml_triage.models.train import TestAccessError, train_and_score
from aml_triage.models.tune import tune_candidate
from aml_triage.utils.logging import get_logger

log = get_logger("aml_triage.lifecycle")


def _guarded(fn):
    def wrapper(args: argparse.Namespace, cfg: Config) -> int:
        try:
            return fn(args, cfg)
        except TestAccessError as exc:
            print(f"test access guard: {exc}", file=sys.stderr)
            return EXIT_GUARD
        except PrerequisiteError as exc:
            print(f"missing prerequisite: {exc}", file=sys.stderr)
            return EXIT_MISSING_PREREQ
        except FileNotFoundError as exc:
            print(f"missing prerequisite: {exc}", file=sys.stderr)
            return EXIT_MISSING_PREREQ
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_VALIDATION

    return wrapper


@_guarded
def run_tune(args: argparse.Namespace, cfg: Config) -> int:
    for mid in [m.strip() for m in args.models.split(",") if m.strip()]:
        log_ = tune_candidate(cfg, mid)
        log.info("tuned %s: best CV %s=%.4f in %.0fs; params=%s", mid, cfg.tuning.scoring, log_["best_cv_score"], log_["seconds"], log_["best_params"])
        # refit on the full training split with the tuned params and refresh validation metrics
        for fset in sorted({cfg.features.default_set, *cfg.features.ablation_sets} & {"primary", "strict_pretx"}):
            res = train_and_score(cfg, mid, fset, "val", context="train")
            log.info("refit %s [%s] val PR-AUC=%.4f fit=%.1fs", mid, fset, res["metrics"]["pr_auc"], res["fit_seconds"])
    print("tuned configs written to configs/models/*.tuned.yaml; validation runs refreshed")
    return EXIT_OK


@_guarded
def run_choose_operating_point(args: argparse.Namespace, cfg: Config) -> int:
    op = choose_operating_point(cfg)
    log.info("selected run %s; threshold=%.4f (F2=%.4f); k_score_cutoff=%.4f; calibration=%s", op["selected_run"], op["threshold"], op["threshold_f2"], op["k_score_cutoff"], op["calibration"]["method"])
    if op.get("frozen_at"):
        print(f"{cfg.operating_point_path} reproduced the frozen operating point exactly; left untouched")
    else:
        print(f"wrote {cfg.operating_point_path}")
    return EXIT_OK


@_guarded
def run_freeze(args: argparse.Namespace, cfg: Config) -> int:
    rec = freeze(cfg)
    if rec.get("noop"):
        print(
            f"already frozen at {rec['frozen_at']} and evaluated at {rec['first_evaluated_at']} for this config hash "
            "and operating point; nothing to do (another test evaluation requires `evaluate --force-reevaluate --reason`)"
        )
        return EXIT_OK
    print(f"frozen at {rec['frozen_at']} (config {rec['config_hash'][:19]}…); test split unlocked for a single `evaluate --split test`")
    return EXIT_OK


@_guarded
def run_evaluate(args: argparse.Namespace, cfg: Config) -> int:
    if args.split != "test":
        print("evaluate is for the test split; validation metrics come from `train --split val` + `compare --split val`", file=sys.stderr)
        return EXIT_VALIDATION
    out = evaluate_test(cfg, force=args.force_reevaluate, reason=args.reason)
    print(f"evaluated {len(out['runs'])} runs on test; state={out['state']['state']}; reevaluations={len(out['state']['reevaluations'])}")
    return EXIT_OK


@_guarded
def run_select(args: argparse.Namespace, cfg: Config) -> int:
    out = select(cfg)
    print(f"selected {out['selected_run']} → {out['bundle_dir']} (models/LATEST = {out['model_version']})")
    return EXIT_OK


@_guarded
def run_reproduce_check(args: argparse.Namespace, cfg: Config) -> int:
    out = reproduce_check(cfg)
    # The README describes the real run only; isolated configurations (smoke/CI, tests) must not rewrite it.
    isolated = cfg.paths.processed_dir != DEFAULT_PROCESSED_DIR
    if isolated:
        readme_note = "README left untouched (isolated configuration)"
    elif Path("README.md").exists():
        render_reproducibility_readme("README.md", out)
        readme_note = "README tolerance section updated"
    else:
        readme_note = "README.md not found in the working directory; tolerance recorded in reports only"
    log.info("reproduce-check %s: exact=%s tolerance=%.3e", out["selected_run"], out["exact"], out["tolerance"])
    print(f"wrote {cfg.paths.reports_dir}/reproducibility.json; {readme_note} (exact={out['exact']})")
    return EXIT_OK


@_guarded
def run_queue(args: argparse.Namespace, cfg: Config) -> int:
    print(f"wrote {write_queue(cfg, args.period)}")
    return EXIT_OK


HANDLERS = {
    "tune": run_tune,
    "choose-operating-point": run_choose_operating_point,
    "freeze": run_freeze,
    "evaluate": run_evaluate,
    "select": run_select,
    "queue": run_queue,
    "reproduce-check": run_reproduce_check,
}
