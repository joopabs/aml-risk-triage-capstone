"""Markdown table and report writers. Every writer appends the disclaimer footer."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from aml_triage.constants import DISCLAIMER
from aml_triage.utils.io import ensure_dir


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        return f"{value:,.4f}" if abs(value) < 1000 else f"{value:,.2f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def md_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    body = ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def disclaimer_footer() -> str:
    return f"\n---\n\n_{DISCLAIMER}_\n"


def write_markdown(path: str | Path, title: str, sections: Sequence[tuple[str, str]]) -> Path:
    """Write ``# title`` followed by ``## heading`` sections and the disclaimer footer."""
    p = Path(path)
    ensure_dir(p.parent)
    parts = [f"# {title}", ""]
    for heading, body in sections:
        parts += [f"## {heading}", "", body.rstrip(), ""]
    parts.append(disclaimer_footer())
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


def narrative_sections(path: str | Path, pending: str) -> list[tuple[str, str]]:
    """Human-authored ``## `` sections from a narrative file, or a single pending placeholder.

    Narrative files keep human text out of generated reports so regeneration never erases it.
    """
    p = Path(path)
    if not p.exists():
        return [("Narrative", pending)]
    out: list[tuple[str, str]] = []
    heading, body = None, []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if heading:
                out.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        elif heading:
            body.append(line)
    if heading:
        out.append((heading, "\n".join(body).strip()))
    return out
