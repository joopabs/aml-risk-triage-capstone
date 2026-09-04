"""Data dictionary generator (spec FR-023): raw columns from the schema, engineered features from
the feature registry when it exists, observed ranges from data_quality.json when it exists."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aml_triage.data.schema import Schema
from aml_triage.reporting.tables import md_table, write_markdown
from aml_triage.utils.io import read_json


class DictionaryError(ValueError):
    """A feature registry entry lacks a rationale or dictionary entry."""


def _observed_range(profile: dict[str, Any] | None, col: str) -> str:
    if not profile:
        return "[PROFILE]"
    ns = profile.get("numeric_summary", {})
    if col in ns:
        return f"{ns[col]['min']:,.2f} – {ns[col]['max']:,.2f}"
    if col == "step" and "steps" in profile:
        return f"{profile['steps']['min_step']} – {profile['steps']['max_step']}"
    if col == "type" and "type_values" in profile:
        return ", ".join(profile["type_values"])
    if col in profile.get("target_by_type", {}) or col in ("isFraud", "isFlaggedFraud"):
        return "0, 1"
    if col in profile.get("identifiers", {}):
        return f"{profile['identifiers'][col]['unique']:,} unique"
    return "[PROFILE]"


def raw_rows(schema: Schema, profile: dict[str, Any] | None) -> list[list[Any]]:
    rows = []
    for c in schema.columns:
        rng = ", ".join(str(a) for a in c.allowed) if c.allowed else _observed_range(profile, c.name)
        rows.append([c.name, c.dtype, c.unit, rng, c.role, c.availability, c.description])
    return rows


def engineered_rows(registry_path: str | Path) -> list[list[Any]]:
    p = Path(registry_path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as fh:
        entries = yaml.safe_load(fh) or []
    rows = []
    for e in entries:
        if not e.get("rationale"):
            raise DictionaryError(f"feature {e.get('name')!r} has no rationale (FR-031)")
        d = e.get("dictionary_entry")
        if not d:
            raise DictionaryError(f"feature {e.get('name')!r} has no dictionary_entry (FR-023)")
        rows.append(
            [
                e["name"],
                d.get("type", ""),
                d.get("unit", ""),
                d.get("range_or_values", ""),
                e.get("kind", "feature"),
                e.get("available_at_prediction_time", ""),
                f"{d.get('description', '')} Rationale: {e['rationale']}",
            ]
        )
    return rows


def build_dictionary(
    schema: Schema,
    out_path: str | Path,
    registry_path: str | Path | None = None,
    profile_path: str | Path | None = None,
) -> Path:
    profile = read_json(profile_path) if profile_path and Path(profile_path).exists() else None
    headers = ["variable", "type", "unit", "range / allowed values", "role", "prediction-time availability", "description"]
    sections = [
        (
            "Conventions",
            "`availability`: `realtime` = known when the transaction is observed; `batch_only` = known "
            "in end-of-period batch triage (post-transaction state, research R-06); `label` = target, "
            "never an input. Identifiers are never model features (FR-033). Observed ranges come from "
            "`reports/data_quality.json`; `[PROFILE]` means profiling has not run yet.",
        ),
        ("Raw variables", md_table(headers, raw_rows(schema, profile))),
    ]
    eng = engineered_rows(registry_path) if registry_path else []
    sections.append(
        (
            "Engineered features",
            md_table(headers, eng) if eng else "_No feature registry yet (configs/features.yaml is created in Milestone 3, task T028)._",
        )
    )
    return write_markdown(out_path, "Data Dictionary", sections)
