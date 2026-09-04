"""Data quality profiling (spec FR-021). Produces aggregates only, never row dumps (FR-015)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aml_triage.data.schema import Schema
from aml_triage.reporting.tables import md_table, write_markdown
from aml_triage.utils.io import write_json

OUTFLOW_TYPES_EXPECTED = ["CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
INFLOW_TYPES_EXPECTED = ["CASH_IN"]


def _q(series: pd.Series, qs=(0.5, 0.95, 0.99, 0.999)) -> dict[str, float]:
    out = {f"p{int(q * 1000) / 10:g}": float(series.quantile(q)) for q in qs}
    out["max"] = float(series.max())
    return out


def _iqr_outliers(series: pd.Series) -> int:
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())


def profile_frame(df: pd.DataFrame, schema: Schema) -> dict[str, Any]:
    """Compute the full data quality profile as a JSON-serialisable dict."""
    tol = schema.balance_tolerance
    ids = schema.by_role("identifier")
    target = schema.by_role("target")[0]
    rule_cols = schema.by_role("rule_comparator")
    numeric = [c.name for c in schema.columns if c.dtype.startswith(("int", "float")) and c.role == "feature"]
    step_col = schema.by_role("time_index")[0]

    out: dict[str, Any] = {"n_rows": int(len(df)), "n_columns": int(df.shape[1])}
    out["columns"] = {c: str(df[c].dtype) for c in df.columns}
    out["nulls"] = {c: int(df[c].isna().sum()) for c in df.columns}
    out["duplicates"] = {
        "exact_rows": int(df.duplicated().sum()),
        "near_duplicates_ignoring_identifiers": int(df.drop(columns=ids).duplicated().sum()),
    }
    out["numeric_summary"] = {
        c: {
            "min": float(df[c].min()),
            "mean": float(df[c].mean()),
            **_q(df[c]),
            "iqr_outliers": _iqr_outliers(df[c]),
            "zeros": int((df[c] == 0).sum()),
            "negatives": int((df[c] < 0).sum()),
        }
        for c in numeric
    }
    out["amount_quantiles_by_type"] = {
        str(t): _q(g["amount"]) for t, g in df.groupby("type", observed=True)
    }

    # Invalid values and balance arithmetic (V5)
    orig_gap = (df["oldbalanceOrg"] - df["newbalanceOrig"] - df["amount"]).abs()
    dest_gap = (df["newbalanceDest"] - df["oldbalanceDest"] - df["amount"]).abs()
    inconsistency = pd.DataFrame(
        {
            "type": df["type"].astype(str),
            "orig_inconsistent": orig_gap > tol,
            "dest_inconsistent": dest_gap > tol,
            "orig_zero_after": (df["oldbalanceOrg"] > 0) & (df["newbalanceOrig"] == 0),
            "dest_both_zero": (df["oldbalanceDest"] == 0) & (df["newbalanceDest"] == 0),
        }
    )
    by_type = inconsistency.groupby("type").agg(["sum", "mean"])
    out["invalid_values"] = {
        "zero_amount": int((df["amount"] == 0).sum()),
        "negative_amount": int((df["amount"] < 0).sum()),
        "negative_balances": {c: int((df[c] < 0).sum()) for c in numeric if "balance" in c},
        "balance_tolerance": tol,
        "orig_balance_inconsistent_total": int(inconsistency["orig_inconsistent"].sum()),
        "dest_balance_inconsistent_total": int(inconsistency["dest_inconsistent"].sum()),
        "by_type": {
            t: {
                "n": int((inconsistency["type"] == t).sum()),
                "orig_inconsistent": int(by_type.loc[t, ("orig_inconsistent", "sum")]),
                "orig_inconsistent_rate": float(by_type.loc[t, ("orig_inconsistent", "mean")]),
                "dest_inconsistent": int(by_type.loc[t, ("dest_inconsistent", "sum")]),
                "dest_inconsistent_rate": float(by_type.loc[t, ("dest_inconsistent", "mean")]),
                "orig_zero_after": int(by_type.loc[t, ("orig_zero_after", "sum")]),
                "dest_both_zero": int(by_type.loc[t, ("dest_both_zero", "sum")]),
            }
            for t in by_type.index
        },
    }

    # Class imbalance (V4)
    y = df[target].astype(int)
    out["target"] = {
        "positives": int(y.sum()),
        "negatives": int((y == 0).sum()),
        "prevalence": float(y.mean()),
        "imbalance_ratio_neg_per_pos": float((y == 0).sum() / max(int(y.sum()), 1)),
    }
    bt = df.groupby("type", observed=True)[target].agg(["count", "sum", "mean"])
    out["target_by_type"] = {
        str(t): {"n": int(r["count"]), "positives": int(r["sum"]), "rate": float(r["mean"])}
        for t, r in bt.iterrows()
    }
    per_step = df.groupby(step_col)[target].agg(["count", "sum"]).rename(columns={"count": "n", "sum": "positives"})
    steps_with_pos = per_step.index[per_step["positives"] > 0]
    out["steps"] = {
        "n_steps": int(per_step.shape[0]),
        "min_step": int(per_step.index.min()),
        "max_step": int(per_step.index.max()),
        "transactions_per_step": {
            "min": int(per_step["n"].min()),
            "median": float(per_step["n"].median()),
            "mean": float(per_step["n"].mean()),
            "max": int(per_step["n"].max()),
        },
        "positives_per_step": {
            "min": int(per_step["positives"].min()),
            "median": float(per_step["positives"].median()),
            "max": int(per_step["positives"].max()),
            "steps_with_zero_positives": int((per_step["positives"] == 0).sum()),
        },
        "first_step_with_positive": int(steps_with_pos.min()) if len(steps_with_pos) else None,
        "last_step_with_positive": int(steps_with_pos.max()) if len(steps_with_pos) else None,
        "cumulative_positives_by_step": {int(k): int(v) for k, v in per_step["positives"].cumsum().items()},
        "transactions_by_step": {int(k): int(v) for k, v in per_step["n"].items()},
    }

    # Identifiers (V3/V10 support)
    out["identifiers"] = {}
    for c in ids:
        vc = df[c].value_counts()
        out["identifiers"][c] = {
            "unique": int(vc.shape[0]),
            "share_appearing_more_than_once": float((vc > 1).sum() / max(vc.shape[0], 1)),
            "max_occurrences": int(vc.max()),
        }

    # Rule comparator column (V6)
    out["rule_flag"] = {}
    for c in rule_cols:
        flag = df[c].astype(int)
        both = int(((flag == 1) & (y == 1)).sum())
        out["rule_flag"][c] = {
            "flagged": int(flag.sum()),
            "flag_rate": float(flag.mean()),
            "flagged_and_positive": both,
            "precision_if_used_as_rule": float(both / flag.sum()) if flag.sum() else None,
            "recall_if_used_as_rule": float(both / y.sum()) if y.sum() else None,
        }

    # Sensitive attribute pre-scan (V7)
    hits = [c for c in df.columns if any(n in c.lower() for n in schema.sensitive_attribute_names)]
    out["sensitive_attribute_prescan"] = {
        "names_checked": schema.sensitive_attribute_names,
        "matching_columns": hits,
        "any_match": bool(hits),
    }
    out["type_values"] = sorted(str(v) for v in df["type"].dropna().unique())
    return out


def render_markdown(profile: dict[str, Any], out_path: str | Path, source_label: str) -> Path:
    """Render the profile to Markdown with a T022 narrative placeholder block."""
    p = profile
    sections: list[tuple[str, str]] = []
    sections.append(
        (
            "Scope",
            f"Source: `{source_label}`. Rows: {p['n_rows']:,}. Columns: {p['n_columns']}. "
            "All figures below are aggregates; no row-level data is shown.",
        )
    )
    sections.append(
        ("Columns and nulls", md_table(["column", "dtype", "nulls"], [(c, p["columns"][c], p["nulls"][c]) for c in p["columns"]]))
    )
    d = p["duplicates"]
    sections.append(
        (
            "Duplicates",
            md_table(["kind", "count"], [("exact duplicate rows", d["exact_rows"]), ("near-duplicates ignoring identifiers", d["near_duplicates_ignoring_identifiers"])]),
        )
    )
    ns = p["numeric_summary"]
    sections.append(
        (
            "Numeric summary and outliers (IQR rule)",
            md_table(
                ["column", "min", "p50", "p95", "p99", "p99.9", "max", "zeros", "negatives", "IQR outliers"],
                [(c, v["min"], v["p50"], v["p95"], v["p99"], v["p99.9"], v["max"], v["zeros"], v["negatives"], v["iqr_outliers"]) for c, v in ns.items()],
            ),
        )
    )
    sections.append(
        (
            "Amount quantiles by transaction type",
            md_table(["type", "p50", "p95", "p99", "p99.9", "max"], [(t, v["p50"], v["p95"], v["p99"], v["p99.9"], v["max"]) for t, v in p["amount_quantiles_by_type"].items()]),
        )
    )
    iv = p["invalid_values"]
    inv_rows = [
        ("zero amount", iv["zero_amount"]),
        ("negative amount", iv["negative_amount"]),
        *[(f"negative {c}", n) for c, n in iv["negative_balances"].items()],
        (f"origin balance arithmetic inconsistent (tol {iv['balance_tolerance']})", iv["orig_balance_inconsistent_total"]),
        (f"destination balance arithmetic inconsistent (tol {iv['balance_tolerance']})", iv["dest_balance_inconsistent_total"]),
    ]
    sections.append(("Invalid values", md_table(["check", "count"], inv_rows)))
    sections.append(
        (
            "Balance arithmetic by type",
            md_table(
                ["type", "n", "orig inconsistent", "rate", "dest inconsistent", "rate", "orig zero after", "dest both zero"],
                [(t, v["n"], v["orig_inconsistent"], v["orig_inconsistent_rate"], v["dest_inconsistent"], v["dest_inconsistent_rate"], v["orig_zero_after"], v["dest_both_zero"]) for t, v in iv["by_type"].items()],
            ),
        )
    )
    tg = p["target"]
    sections.append(
        (
            "Class imbalance",
            md_table(["metric", "value"], [("positives (simulated fraud)", tg["positives"]), ("negatives", tg["negatives"]), ("prevalence", tg["prevalence"]), ("negatives per positive", tg["imbalance_ratio_neg_per_pos"])])
            + "\n\n"
            + md_table(["type", "n", "positives", "rate"], [(t, v["n"], v["positives"], v["rate"]) for t, v in p["target_by_type"].items()]),
        )
    )
    st = p["steps"]
    tps, pps = st["transactions_per_step"], st["positives_per_step"]
    sections.append(
        (
            "Time steps",
            md_table(
                ["metric", "value"],
                [
                    ("steps observed", st["n_steps"]),
                    ("step range", f"{st['min_step']}–{st['max_step']}"),
                    ("transactions per step (min / median / max)", f"{tps['min']:,} / {tps['median']:,.0f} / {tps['max']:,}"),
                    ("positives per step (min / median / max)", f"{pps['min']} / {pps['median']:.0f} / {pps['max']}"),
                    ("steps with zero positives", pps["steps_with_zero_positives"]),
                    ("first / last step with a positive", f"{st['first_step_with_positive']} / {st['last_step_with_positive']}"),
                ],
            )
            + "\n\nPer-step counts are in `data_quality.json` under `steps.transactions_by_step` and `steps.cumulative_positives_by_step` (used to choose split bounds, V9).",
        )
    )
    sections.append(
        (
            "Identifiers",
            md_table(["column", "unique", "share appearing >1", "max occurrences"], [(c, v["unique"], v["share_appearing_more_than_once"], v["max_occurrences"]) for c, v in p["identifiers"].items()]),
        )
    )
    if p["rule_flag"]:
        sections.append(
            (
                "Rule flag column",
                md_table(["column", "flagged", "rate", "flagged and positive", "precision as rule", "recall as rule"], [(c, v["flagged"], v["flag_rate"], v["flagged_and_positive"], v["precision_if_used_as_rule"], v["recall_if_used_as_rule"]) for c, v in p["rule_flag"].items()]),
            )
        )
    sa = p["sensitive_attribute_prescan"]
    sections.append(
        (
            "Sensitive-attribute pre-scan",
            f"Column names checked against: {', '.join(sa['names_checked'])}.\n\n"
            + (f"Matching columns: {sa['matching_columns']}" if sa["any_match"] else "No column name matches a sensitive-attribute pattern. The formal availability record is produced in Milestone 7 (FR-070)."),
        )
    )
    sections.append(
        (
            "Findings and handling decisions",
            "<!-- T022: written by a human after reviewing the tables above. One row per finding, "
            "decision ids DQ-01..., decision in {keep, correct, flag as feature, exclude}, with justification. -->\n\n"
            "_Pending review (task T022)._",
        )
    )
    sections.append(
        (
            "Source-data limitations",
            "<!-- T022: written after review. Synthetic generation, simulator artifacts, label validity, "
            "transferability. -->\n\n_Pending review (task T022)._",
        )
    )
    return write_markdown(out_path, "Data Quality Report", sections)


def run_profile(df: pd.DataFrame, schema: Schema, reports_dir: str | Path, source_label: str) -> tuple[Path, Path]:
    prof = profile_frame(df, schema)
    reports_dir = Path(reports_dir)
    json_path = write_json(prof, reports_dir / "data_quality.json")
    md_path = render_markdown(prof, reports_dir / "data_quality.md", source_label)
    return md_path, json_path


__all__ = ["profile_frame", "render_markdown", "run_profile", "np"]
