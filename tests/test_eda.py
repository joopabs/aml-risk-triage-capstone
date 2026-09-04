from __future__ import annotations

from pathlib import Path

import yaml

from aml_triage.config import load
from aml_triage.constants import DISCLAIMER
from aml_triage.data.split import make_split, write_split
from aml_triage.eda.plots import run_eda
from aml_triage.features.pipeline import build_feature_matrices


def test_eda_runs_on_fixture_and_writes_summary(
    tmp_path: Path, repo_root: Path, fixture_frame
) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "processed_dir": str(tmp_path / "processed"),
                    "reports_dir": str(tmp_path / "reports"),
                    "raw_csv": str(tmp_path / "f.csv"),
                },
                "split": {"train_end_step": 40, "val_end_step": 56, "min_positives_per_split": 1},
                "review": {"review_period_steps": 24, "primary_k": 5, "k_grid": [5, 10]},
            }
        )
    )
    cfg = load(cfg_path)
    parts, manifest = make_split(fixture_frame, cfg)
    write_split(parts, manifest, cfg.paths.processed_dir)
    build_feature_matrices(cfg, "primary")
    (tmp_path / "reports").mkdir(exist_ok=True)
    (tmp_path / "reports" / "eda_narrative.md").write_text(
        "### eda_01_class_by_type.png\nfixture observation\n"
    )
    summary, figures = run_eda(cfg, n_neg_sample=200)
    assert len(figures) == 11
    assert all(Path(p).exists() for p, _ in figures)
    text = summary.read_text()
    assert DISCLAIMER in text
    assert "Observation: fixture observation" in text
    assert text.count("\nObservation:") == 11  # ten empty on the fixture, one filled
