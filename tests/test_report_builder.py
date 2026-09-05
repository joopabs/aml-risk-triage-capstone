from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aml_triage.config import load
from aml_triage.constants import DISCLAIMER
from aml_triage.reporting.report_builder import SECTIONS, MissingSectionError, build_report


def test_build_report_requires_every_section_and_assembles(tmp_path: Path, repo_root: Path) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "reports_dir": str(tmp_path / "reports"),
                    "models_dir": str(tmp_path / "models"),
                },
            }
        )
    )
    cfg = load(cfg_path)
    reports = tmp_path / "reports"
    (reports / "sections").mkdir(parents=True)
    with pytest.raises(MissingSectionError):
        build_report(cfg)
    for _, files in SECTIONS:
        for f in files:
            (reports / f).write_text(
                f"# {Path(f).stem}\n\n## Part\n\ntext of {f}\n\n---\n\n_{DISCLAIMER}_\n"
            )
    out = build_report(cfg, version="vtest")
    text = out.read_text()
    assert text.count(DISCLAIMER) == 2  # front matter + single footer; per-file footers stripped
    for title, _ in SECTIONS:
        assert f"## {title}" in text
    import re

    assert not re.search(r"^### Part$", text, re.M)
    assert re.search(r"^#### Part$", text, re.M)  # demoted by two levels
