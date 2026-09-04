"""freeze → evaluate (single-touch test) → select (bundle) → queue. Data-model §9, §10, §11, §7."""

from __future__ import annotations

import concurrent.futures
import json
import multiprocessing
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from aml_triage.config import Config
from aml_triage.constants import DISCLAIMER, SYNTHETIC_NOTICE
from aml_triage.data.split import MANIFEST_NAME, SplitManifest
from aml_triage.evaluation.bootstrap import bootstrap_ci
from aml_triage.evaluation.capacity import rank_within_periods
from aml_triage.evaluation.capacity_report import capacity_report
from aml_triage.evaluation.compare import compare, render_selection_matrix, selection_matrix
from aml_triage.evaluation.metrics import compute_metrics
from aml_triage.evaluation.threshold import apply_operating_point, assign_priority, load_operating_point
from aml_triage.models.train import TEST_ACCESS, TestAccessError, list_runs, load_run, runs_dir, test_access_state, train_and_score
from aml_triage.reporting.tables import md_table, write_markdown
from aml_triage.utils.io import ensure_dir, load_joblib, model_version, read_json, save_joblib, sha256_file, write_json

QUEUE_COLUMNS = ["rank", "row_index", "step", "type", "risk_score", "review_priority", "model_version"]


class PrerequisiteError(RuntimeError):
    """A required artifact is missing (exit code 4)."""


# ---- freeze -----------------------------------------------------------------------------------
def freeze(cfg: Config) -> dict[str, Any]:
    op = load_operating_point(cfg)
    if op is None:
        raise PrerequisiteError(f"{cfg.operating_point_path} not found; run `choose-operating-point` first")
    processed = Path(cfg.paths.processed_dir)
    state = test_access_state(processed)
    if state.get("state") == "evaluated" or state.get("first_evaluated_at"):
        raise TestAccessError(f"test split already evaluated at {state.get('first_evaluated_at')}; the operating point cannot be re-frozen")
    refreezes = list(state.get("refreezes", []))
    if state.get("state") == "frozen":
        refreezes.append({"previous_frozen_at": state.get("frozen_at"), "previous_operating_point": state.get("operating_point")})
    now = datetime.now(UTC).isoformat(timespec="seconds")
    record = {"config_hash": cfg.config_hash(), "state": "frozen", "frozen_at": now, "first_evaluated_at": None, "reevaluations": [], "refreezes": refreezes, "operating_point": {k: op[k] for k in ("selected_run", "threshold", "primary_k", "k_score_cutoff")}}
    (processed / TEST_ACCESS).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    op["frozen_at"] = now
    Path(cfg.operating_point_path).write_text("# Frozen; do not edit. Written by `choose-operating-point`, sealed by `freeze`.\n" + yaml.safe_dump(op, sort_keys=False), encoding="utf-8")
    mp = processed / MANIFEST_NAME
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    manifest["frozen_at"] = now
    mp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


# ---- evaluate ---------------------------------------------------------------------------------
def evaluate_test(cfg: Config, force: bool = False, reason: str | None = None) -> dict[str, Any]:
    processed = Path(cfg.paths.processed_dir)
    state = test_access_state(processed)
    if state.get("state") == "locked":
        raise TestAccessError("test split is locked; run `choose-operating-point` then `freeze` first")
    if state.get("config_hash") != cfg.config_hash():
        raise TestAccessError("config hash changed since freeze; re-split/re-freeze under a new model version instead of evaluating")
    if state.get("first_evaluated_at"):
        if not force:
            raise TestAccessError(f"test split already evaluated at {state['first_evaluated_at']} for this config hash; pass --force-reevaluate --reason \"...\"")
        if not reason or not reason.strip():
            raise TestAccessError("--force-reevaluate requires --reason")
        state["reevaluations"].append({"timestamp": datetime.now(UTC).isoformat(timespec="seconds"), "reason": reason.strip()})
    results = {}
    # Each refit runs in a fresh subprocess so memory is returned to the OS between runs
    # (a single long-lived process was killed for memory on the 16 GB development machine).
    ctx = multiprocessing.get_context("spawn")
    for rid in list_runs(cfg, "val"):
        with concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=ctx) as pool:
            results[rid] = pool.submit(_evaluate_one, str(cfg.source_path), cfg.seed, rid).result()
    state["state"] = "evaluated"
    state["first_evaluated_at"] = state.get("first_evaluated_at") or datetime.now(UTC).isoformat(timespec="seconds")
    (processed / TEST_ACCESS).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    compare(cfg, "test")
    return {"state": state, "runs": list(results)}


def _evaluate_one(config_path: str, seed: int, rid: str) -> dict[str, Any]:
    """Refit one run on train, score test once, add operating-point metrics and bootstrap CIs."""
    import gc

    from aml_triage.config import load as load_cfg

    cfg = load_cfg(config_path, overrides={"seed": seed})
    op = load_operating_point(cfg) or {}
    mid, fset = rid.split("__", 1)
    res = train_and_score(cfg, mid, fset, "test", context="evaluate")
    _, preds = load_run(cfg, rid, "test")
    if rid == op.get("selected_run"):
        cal = apply_operating_point(op, preds)
        res["operating_point_metrics"] = compute_metrics(cal["isFraud"], cal["score"], threshold=float(op["threshold"]), degenerate_eps=cfg.evaluation.degenerate_eps)
        res["operating_point_metrics"]["calibration_applied"] = bool((op.get("calibration") or {}).get("applied"))
        calq = compute_metrics(cal["isFraud"], cal["calibrated_score"], threshold=0.5, degenerate_eps=cfg.evaluation.degenerate_eps)
        res["operating_point_metrics"]["calibrated_probability"] = {"brier": calq["brier"], "ece": calq["ece"], "pr_auc": calq["pr_auc"], "note": "display probability after validation-fitted isotonic; ranking uses raw scores"}
    res["bootstrap_ci"] = bootstrap_ci(preds, cfg.review.primary_k, cfg.review.review_period_steps, cfg.bootstrap.n_resamples, cfg.seed)
    write_json(res, runs_dir(cfg) / rid / "test_metrics.json")
    gc.collect()
    return {k: v for k, v in res.items() if k in ("candidate_id", "feature_set", "metrics", "bootstrap_ci")}


# ---- select -----------------------------------------------------------------------------------
def select(cfg: Config, headline_set: str | None = None) -> dict[str, Any]:
    headline_set = headline_set or cfg.features.default_set
    op = load_operating_point(cfg)
    if op is None or not op.get("frozen_at"):
        raise PrerequisiteError("operating point must be chosen and frozen before `select`")
    if not list_runs(cfg, "test"):
        raise PrerequisiteError("no test metrics; run `evaluate --split test` first")
    matrix = selection_matrix(cfg, headline_set)
    if matrix["selected_run"] != op["selected_run"]:
        raise TestAccessError(f"selection matrix picks {matrix['selected_run']} but the frozen operating point is for {op['selected_run']}; selection must not change after freeze")
    render_selection_matrix(cfg, matrix)

    rid = op["selected_run"]
    mid, fset = rid.split("__", 1)
    version = model_version(mid)
    bundle_dir = ensure_dir(Path(cfg.paths.models_dir) / version)
    processed = Path(cfg.paths.processed_dir)
    val_metrics, _ = load_run(cfg, rid, "val")
    test_metrics, _ = load_run(cfg, rid, "test")
    bundle = {
        "model_version": version,
        "candidate_id": mid,
        "feature_set": fset,
        "feature_pipeline": load_joblib(processed / f"feature_pipeline_{fset}.joblib"),
        "estimator": load_joblib(runs_dir(cfg) / rid / f"model_{fset}.joblib"),
        "calibrator": load_joblib(op["calibration"]["calibrator_path"]) if (op.get("calibration") or {}).get("calibrator_path") else None,
        "operating_point": op,
        "feature_list": read_json(processed / f"features_{fset}.json")["features"],
        "registry_features": read_json(processed / f"features_{fset}.json")["registry_features"],
        "disclaimer": DISCLAIMER,
    }
    pipe_path = save_joblib(bundle, bundle_dir / "pipeline.joblib")
    (bundle_dir / "pipeline.sha256").write_text(sha256_file(pipe_path) + "\n", encoding="utf-8")
    snapshot = {"effective_config": cfg.model_dump(mode="json"), "operating_point": op, "split_manifest": SplitManifest.read(processed / MANIFEST_NAME).__dict__, "config_hash": cfg.config_hash()}
    (bundle_dir / "config_snapshot.yaml").write_text(yaml.safe_dump(snapshot, sort_keys=False, default_flow_style=False), encoding="utf-8")
    write_json({"val": val_metrics, "test": test_metrics}, bundle_dir / "metrics.json")
    write_json({"feature_set": fset, "features": bundle["feature_list"], "registry_features": bundle["registry_features"]}, bundle_dir / "feature_list.json")
    shutil.copy(Path(cfg.features.registry), bundle_dir / "features.yaml")
    write_model_card(cfg, bundle_dir, version, mid, fset, op, val_metrics, test_metrics)
    (Path(cfg.paths.models_dir) / "LATEST").write_text(version + "\n", encoding="utf-8")
    capacity_report(cfg, rid)
    return {"model_version": version, "bundle_dir": str(bundle_dir), "selected_run": rid}


def write_model_card(cfg, bundle_dir: Path, version: str, mid: str, fset: str, op: dict, val: dict, test: dict) -> Path:
    K = str(cfg.review.primary_k)
    ci = test.get("bootstrap_ci") or {}
    opm = test.get("operating_point_metrics") or {}

    def row(split, m):
        return (split, m["metrics"]["pr_auc"], m["metrics"]["roc_auc"], m["recall_at_k"][K]["mean_over_periods"], m["recall_at_k"][K]["pooled"], m["precision_at_k"][K]["mean_over_periods"], m["metrics"]["brier"], m["metrics"]["ece"])

    sections = [
        ("Model Details", f"Version `{version}`; candidate `{mid}` on feature set `{fset}`; trained on {val['n_train_rows']:,} training rows ({val['n_train_positives']:,} positives); tuned parameters used: {val.get('tuned_params_used')}. Pipeline checksum in `pipeline.sha256`."),
        ("Intended Use", "Educational decision-support prototype that ranks synthetic PaySim transactions so a fixed daily investigator capacity is spent on the transactions most worth a human look. Outputs: risk score, review priority (high/medium/low), model version, disclaimer."),
        ("Non-Use", "No automatic blocking, account closure, customer risk rating, regulatory reporting, or AML determination. Not validated for real customer data; a governance-controlled validation and fairness audit would be required before any real use."),
        ("Data", f"{SYNTHETIC_NOTICE} Source and license recorded in `data/README.md` and `configs/data_source.yaml` (CC BY-SA 4.0). Temporal split: train steps 1–408, validation 409–552, test 553–743."),
        ("Metrics", md_table(["split", "PR-AUC", "ROC-AUC", f"Recall@{K} mean", f"Recall@{K} pooled", f"Precision@{K}", "Brier", "ECE"], [row("validation", val), row("test", test)]) + f"\n\nTest 95% bootstrap CIs ({ci.get('n_resamples')} resamples): PR-AUC {ci.get('pr_auc')}, pooled Recall@{K} {ci.get('recall_at_k_pooled')}."),
        ("Operating Point", f"Chosen on validation only. Threshold {op['threshold']} (rule {op['threshold_rule']}); priority rule {op['priority_rule']}; K-th score cutoff {op['k_score_cutoff']}; calibration `{op['calibration']['method']}` (applied: {op['calibration']['applied']}). " + (f"Test metrics at the operating point: precision {opm.get('precision'):.4f}, recall {opm.get('recall'):.4f}, FPR {opm.get('fpr'):.6f}, confusion {opm.get('confusion_matrix')}." if opm else "")),
        ("Explainability Summary", "See `reports/explainability.md` (Milestone 7): SHAP global and local explanations, PDP/ICE where valid."),
        ("Limitations", "Near-perfect separability is a property of the PaySim generator, not evidence of AML capability. Validation and test prevalence exceed training prevalence by an order of magnitude (simulator injects positives at a constant rate). Several strong features are simulator artifacts (balance bookkeeping, zero amounts). Results cannot establish real-world detection effectiveness, fairness, or regulatory suitability."),
        ("Fairness Statement", "Sensitive-attribute availability is recorded in Milestone 7 (`reports/fairness_availability.json`); PaySim carries no demographic attributes, so only an operational error-slice analysis is possible."),
        ("Version and Checksums", f"`models/LATEST` → `{version}`; `pipeline.sha256` holds the SHA-256 of `pipeline.joblib` (the joblib file is regenerated with `make pipeline` and is not committed)."),
    ]
    return write_markdown(bundle_dir / "model_card.md", f"Model Card: {mid} [{fset}] {version}", sections)


# ---- queue ------------------------------------------------------------------------------------
def write_queue(cfg: Config, period_ordinal: int) -> Path:
    op = load_operating_point(cfg)
    if op is None:
        raise PrerequisiteError("operating point not found; run `choose-operating-point`")
    latest = Path(cfg.paths.models_dir) / "LATEST"
    version = latest.read_text().strip() if latest.exists() else "unreleased"
    rid = op["selected_run"]
    try:
        _, preds = load_run(cfg, rid, "test")
        split = "test"
    except FileNotFoundError:
        _, preds = load_run(cfg, rid, "val")
        split = "val"
    cal = apply_operating_point(op, preds)
    ranked = rank_within_periods(cal[["row_index", "step", "isFraud", "score", "calibrated_score"]].join(cal["type"]), cfg.review.review_period_steps)
    periods = sorted(ranked["period"].unique())
    if not 0 <= period_ordinal < len(periods):
        raise PrerequisiteError(f"period ordinal {period_ordinal} out of range 0..{len(periods) - 1} for the {split} split")
    period = periods[period_ordinal]
    g = ranked[ranked["period"] == period].copy()
    g["review_priority"] = assign_priority(g, op)
    k = int(op["primary_k"])
    top = g[g["rank"] <= min(k, len(g))]
    rows = [(int(r.rank), int(r.row_index), int(r.step), str(r.type), round(float(r.calibrated_score), 6), r.review_priority, version) for r in top.itertuples()]
    shortfall = k - len(top)
    sections = [
        ("Scope", f"{split} split, review period ordinal {period_ordinal} (simulated day {int(period) + 1}, steps {int(g['step'].min())}–{int(g['step'].max())}); {len(g):,} transactions in the period; capacity K = {k}; model `{rid}` version `{version}`; ranking uses raw model scores, `risk_score` shows the validation-calibrated probability (calibration applied: {op['calibration']['applied']}). Labels are hidden from the queue; investigators review, decide, and may override."),
        ("Queue", md_table(QUEUE_COLUMNS, rows) + (f"\n\n**Shortfall:** only {len(top)} transactions exist in this period, {shortfall} below capacity." if shortfall > 0 else "")),
    ]
    return write_markdown(Path(cfg.paths.reports_dir) / f"review_queue_period_{period_ordinal}.md", f"Review Queue — period {period_ordinal}", sections)


__all__ = ["freeze", "evaluate_test", "select", "write_queue", "PrerequisiteError", "pd"]
