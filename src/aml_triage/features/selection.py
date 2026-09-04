"""Feature selection on the training split only (spec FR-034, research R-08).

Two methods, both fitted on a seeded stratified training subsample:
* filter  — mutual information (``SelectKBest(mutual_info_classif, k=mi_k)``)
* embedded — L1-penalised logistic regression (``SelectFromModel``), features standardised first
Combine rule (config): intersection, or the union if the intersection has fewer than ``min_size``.
Selection works on matrix columns; the registry ``selected`` set is the registry features that own
at least one selected column (all ``type_*`` columns belong to ``type_onehot``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectFromModel, SelectKBest, mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from aml_triage.config import Config
from aml_triage.features.base import load_registry
from aml_triage.features.pipeline import FitScopeRecorder, assert_fit_scope, load_feature_matrix
from aml_triage.reporting.tables import md_table, narrative_sections, write_markdown
from aml_triage.utils.io import write_json

NARRATIVE_FILENAME = "feature_selection_narrative.md"


def registry_name(column: str) -> str:
    return "type_onehot" if column.startswith("type_") else column


def stratified_subsample(
    X: pd.DataFrame, y: pd.Series, n_rows: int, seed: int
) -> tuple[pd.DataFrame, pd.Series]:
    if n_rows >= len(X):
        return X, y
    Xs, _, ys, _ = train_test_split(X, y, train_size=n_rows, stratify=y, random_state=seed)
    return Xs, ys


def run_selection(cfg: Config, set_name: str = "primary") -> dict[str, Any]:
    processed = Path(cfg.paths.processed_dir)
    X, meta = load_feature_matrix(processed, set_name, "train")
    y = meta["isFraud"].astype(int)
    n_rows = cfg.tuning.tune_sample_rows or len(X)
    Xs, ys = stratified_subsample(X, y, n_rows, cfg.seed)
    before = list(X.columns)
    constant = [c for c in before if Xs[c].nunique() <= 1]

    k = min(cfg.selection.mi_k or len(before), len(before))
    mi = FitScopeRecorder(SelectKBest(mutual_info_classif, k=k))
    mi.transformer.score_func = lambda a, b: mutual_info_classif(
        a, b, random_state=cfg.seed, n_jobs=cfg.compute.n_jobs
    )
    mi.fit(Xs, ys, split_id="train")
    mi_scores = pd.Series(mi.transformer.scores_, index=before).sort_values(ascending=False)
    mi_selected = [c for c in before if c in set(mi_scores.index[:k])]

    l1 = FitScopeRecorder(
        Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "select",
                    SelectFromModel(
                        LogisticRegression(
                            penalty="l1",
                            C=cfg.selection.l1_c or 0.1,
                            solver="liblinear",
                            class_weight="balanced",
                            random_state=cfg.seed,
                            max_iter=2000,
                        ),
                        threshold=1e-6,
                    ),
                ),
            ]
        )
    )
    l1.fit(Xs, ys, split_id="train")
    coefs = pd.Series(l1.transformer.named_steps["select"].estimator_.coef_.ravel(), index=before)
    l1_selected = [c for c in before if abs(coefs[c]) > 1e-6]

    inter = [c for c in before if c in set(mi_selected) & set(l1_selected)]
    rule = cfg.selection.combine_rule
    min_size = cfg.selection.min_size or 1
    if rule == "intersection_or_union_if_lt" and len(inter) < min_size:
        combined = [c for c in before if c in set(mi_selected) | set(l1_selected)]
        rule_applied = f"union (intersection had {len(inter)} < min_size {min_size})"
    else:
        combined = inter
        rule_applied = f"intersection ({len(inter)} >= min_size {min_size})"
    combined = [c for c in combined if c not in constant]
    selected_registry = sorted(
        {registry_name(c) for c in combined},
        key=lambda n: [registry_name(c) for c in before].index(n),
    )

    for rec in (mi, l1):
        assert_fit_scope(rec.record())

    result = {
        "feature_set": set_name,
        "subsample_rows": int(len(Xs)),
        "subsample_positives": int(ys.sum()),
        "before": before,
        "constant_columns": constant,
        "mi_k": k,
        "mi_scores": {c: float(v) for c, v in mi_scores.items()},
        "mi_selected": mi_selected,
        "l1_c": cfg.selection.l1_c,
        "l1_coefficients": {c: float(coefs[c]) for c in before},
        "l1_selected": l1_selected,
        "intersection": inter,
        "combine_rule": rule,
        "rule_applied": rule_applied,
        "selected_columns": combined,
        "selected_registry_features": selected_registry,
        "dropped_columns": [c for c in before if c not in combined],
        "fit_scope": {"mi": mi.record(), "l1": l1.record()},
        "config_hash": cfg.config_hash(),
    }
    return result


def update_registry_selected(registry_path: str | Path, selected_registry: list[str]) -> Path:
    """Add/remove ``selected`` in each entry's ``sets:`` line, preserving comments and order."""
    p = Path(registry_path)
    text = p.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^(?=- name: )", text)
    out = []
    for block in blocks:
        m = re.match(r"- name: (\S+)", block)
        if m:
            name = m.group(1)

            def repl(sm: re.Match[str], name: str = name) -> str:
                items = [
                    s.strip()
                    for s in sm.group(1).split(",")
                    if s.strip() and s.strip() != "selected"
                ]
                if name in selected_registry:
                    items.append("selected")
                return f"  sets: [{', '.join(items)}]"

            block = re.sub(r"(?m)^  sets: \[([^\]]*)\]", repl, block, count=1)
        out.append(block)
    p.write_text("".join(out), encoding="utf-8")
    load_registry(p)  # validate
    return p


def render_report(result: dict[str, Any], reports_dir: str | Path) -> Path:
    reports = Path(reports_dir)
    mi_rows = [
        (c, v, "yes" if c in result["mi_selected"] else "")
        for c, v in sorted(result["mi_scores"].items(), key=lambda kv: -kv[1])
    ]
    l1_rows = [
        (c, v, "yes" if c in result["l1_selected"] else "")
        for c, v in sorted(result["l1_coefficients"].items(), key=lambda kv: -abs(kv[1]))
    ]
    sections = [
        (
            "Scope",
            f"Feature set `{result['feature_set']}`, training split only, seeded stratified subsample of "
            f"{result['subsample_rows']:,} rows with {result['subsample_positives']:,} positives (research R-08). "
            f"Fit scope: MI {result['fit_scope']['mi']['fitted_on']}, L1 {result['fit_scope']['l1']['fitted_on']}.",
        ),
        (
            "Before",
            f"{len(result['before'])} columns: "
            + ", ".join(f"`{c}`" for c in result["before"])
            + (
                f"\n\nConstant columns (no information on the subsample): {', '.join(f'`{c}`' for c in result['constant_columns']) or 'none'}"
            ),
        ),
        (
            f"Filter method: mutual information (top {result['mi_k']})",
            md_table(["column", "MI score", "selected"], mi_rows),
        ),
        (
            f"Embedded method: L1 logistic regression (C = {result['l1_c']}, standardised inputs, balanced class weight)",
            md_table(["column", "coefficient", "non-zero"], l1_rows),
        ),
        (
            "After",
            f"Intersection ({len(result['intersection'])}): "
            + (", ".join(f"`{c}`" for c in result["intersection"]) or "none")
            + "\n\n"
            f"Combine rule `{result['combine_rule']}` → **{result['rule_applied']}**.\n\n"
            f"**Selected columns ({len(result['selected_columns'])})**: "
            + ", ".join(f"`{c}`" for c in result["selected_columns"])
            + "\n\n"
            f"**Dropped columns ({len(result['dropped_columns'])})**: "
            + (", ".join(f"`{c}`" for c in result["dropped_columns"]) or "none")
            + "\n\n"
            f"**Registry `selected` set ({len(result['selected_registry_features'])} features)**: "
            + ", ".join(f"`{c}`" for c in result["selected_registry_features"]),
        ),
    ]
    sections += narrative_sections(
        reports / NARRATIVE_FILENAME,
        "<!-- Task T041: write reports/feature_selection_narrative.md after reviewing the tables above. -->\n\n_Pending review (task T041)._",
    )
    write_json(result, reports / "feature_selection.json")
    return write_markdown(reports / "feature_selection.md", "Feature Selection", sections)


__all__ = ["run_selection", "update_registry_selected", "render_report", "registry_name", "np"]
