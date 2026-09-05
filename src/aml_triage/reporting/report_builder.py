"""Assemble reports/final_report.md from generated section reports and hand-authored sections (FR-090)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from aml_triage.config import Config
from aml_triage.constants import DISCLAIMER, SYNTHETIC_NOTICE
from aml_triage.reporting.tables import disclaimer_footer

# (section title, [source files relative to reports/])
SECTIONS: list[tuple[str, list[str]]] = [
    ("1. Problem Statement", ["sections/01_problem.md"]),
    ("2. Dataset Overview and Data Dictionary", ["data_quality.md", "data_dictionary.md"]),
    (
        "3. EDA and Feature Engineering Report",
        ["eda_summary.md", "feature_selection.md", "pca_report.md"],
    ),
    (
        "4. Model Comparison and Selection",
        ["model_comparison.md", "selection_matrix.md", "capacity_analysis.md"],
    ),
    ("5. Explainability", ["explainability.md"]),
    ("6. Bias & Fairness Analysis", ["bias_fairness_analysis.md"]),
    ("7. Limitations", ["sections/07_limitations.md"]),
    ("8. Reproducibility", ["sections/08_reproducibility.md"]),
]


class MissingSectionError(FileNotFoundError):
    """A required section file is missing (exit code 4)."""


def _strip_footer(text: str) -> str:
    """Remove a per-report disclaimer footer; the assembled report carries one footer at the end."""
    marker = disclaimer_footer().strip()
    return text.replace(marker, "").rstrip() + "\n"


def _demote(text: str, levels: int = 2) -> str:
    """Drop the file's H1 and push every other heading down by ``levels``."""
    out = []
    for line in text.splitlines():
        if re.match(r"^# ", line):
            continue  # file title becomes the subsection name we add ourselves
        m = re.match(r"^(#{2,6}) (.*)$", line)
        if m:
            line = "#" * min(6, len(m.group(1)) + levels) + " " + m.group(2)
        out.append(line)
    return "\n".join(out)


def _subsection_name(path: Path) -> str:
    first = path.read_text(encoding="utf-8").splitlines()[0] if path.exists() else path.stem
    return first[2:].strip() if first.startswith("# ") else path.stem.replace("_", " ").title()


def build_report(cfg: Config, version: str | None = None) -> Path:
    reports = Path(cfg.paths.reports_dir)
    missing = [f for _, files in SECTIONS for f in files if not (reports / f).exists()]
    if missing:
        raise MissingSectionError(f"missing report section files: {missing}")
    latest = Path(cfg.paths.models_dir) / "LATEST"
    version = version or (latest.read_text().strip() if latest.exists() else "unreleased")
    today = datetime.now(UTC).date().isoformat()

    parts = [
        "# Explainable AML Transaction-Risk Triage for SME and Corporate Banking",
        "",
        "**Final report — Pillar 5 Capstone Project**",
        "",
        f"Author: Julius Pabular · Date: {today} · Released model: `{version}` · Repository: https://github.com/joopabs/aml-risk-triage-capstone",
        "",
        f"> {DISCLAIMER}",
        ">",
        f"> {SYNTHETIC_NOTICE}",
        "",
        "## Contents",
        "",
        *[
            f"{i + 1}. [{title[3:]}](#{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')})"
            for i, (title, _) in enumerate(SECTIONS)
        ],
        "",
    ]
    for title, files in SECTIONS:
        parts += [f"## {title}", ""]
        for f in files:
            p = reports / f
            body = _demote(_strip_footer(p.read_text(encoding="utf-8")))
            if len(files) > 1 or not f.startswith("sections/"):
                parts += [f"### {_subsection_name(p)}", ""]
            parts += [body.strip(), ""]
    parts.append(disclaimer_footer())
    out = reports / "final_report.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out
