"""Every notebook code cell must at least compile; execution is verified per milestone via nbconvert."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parents[1] / "notebooks").glob("*.ipynb"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=[p.name for p in NOTEBOOKS])
def test_notebook_code_cells_compile(path: Path) -> None:
    nb = json.loads(path.read_text(encoding="utf-8"))
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"{path.name}:cell{i}", "exec")
