"""FR-101: run parameters come from configs/, never from literals in notebooks or scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path

PARAMS = [
    "seed",
    "K",
    "k",
    "primary_k",
    "train_end_step",
    "val_end_step",
    "threshold",
    "review_period_steps",
]
LITERAL_ASSIGNMENT = re.compile(
    r"^\s*(?:" + "|".join(re.escape(p) for p in PARAMS) + r")\s*=\s*-?\d+(?:\.\d+)?\s*(?:#.*)?$",
    re.MULTILINE,
)


def find_hardcoded(code: str) -> list[str]:
    return [m.group(0).strip() for m in LITERAL_ASSIGNMENT.finditer(code)]


def _notebook_code(path: Path) -> str:
    nb = json.loads(path.read_text(encoding="utf-8"))
    return "\n".join(
        "".join(c.get("source", [])) for c in nb.get("cells", []) if c.get("cell_type") == "code"
    )


def test_detector_self_check() -> None:
    assert find_hardcoded("seed = 42\nK = 100  # capacity\n") == [
        "seed = 42",
        "K = 100  # capacity",
    ]
    assert find_hardcoded("seed = cfg.seed\nK = cfg.review.primary_k\n") == []
    assert find_hardcoded("threshold_rule = 'f2'\nseeds = [1, 2]\n") == []


def test_notebooks_and_scripts_read_parameters_from_config(repo_root: Path) -> None:
    offenders: dict[str, list[str]] = {}
    for nb in (repo_root / "notebooks").glob("*.ipynb"):
        hits = find_hardcoded(_notebook_code(nb))
        if hits:
            offenders[str(nb.relative_to(repo_root))] = hits
    for script in (repo_root / "scripts").glob("*.py"):
        hits = find_hardcoded(script.read_text(encoding="utf-8"))
        if hits:
            offenders[str(script.relative_to(repo_root))] = hits
    assert not offenders, f"hardcoded run parameters found: {offenders}"
