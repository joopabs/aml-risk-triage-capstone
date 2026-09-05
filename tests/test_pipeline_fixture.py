"""End-to-end CLI chain on a synthetic frame: selection, PCA, tuning, operating point, single-touch
test, selection bundle, explain, fairness, report. Mirrors the CI smoke pipeline at fixture scale."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aml_triage.cli import main
from aml_triage.constants import DISCLAIMER, EXIT_OK
from aml_triage.utils.synthetic import make_synthetic_frame


@pytest.fixture(scope="module")
def chain(tmp_path_factory, repo_root) -> tuple[Path, Path]:
    import shutil

    tmp = tmp_path_factory.mktemp("chain")
    models_cfg = tmp / "models_cfg"
    models_cfg.mkdir()
    for f in (repo_root / "configs" / "models").glob("*.yaml"):
        if ".tuned" not in f.name:
            shutil.copy(f, models_cfg / f.name)
    reg = tmp / "features.yaml"
    shutil.copy(repo_root / "configs" / "features.yaml", reg)
    raw = tmp / "sample.csv"
    make_synthetic_frame(
        seed=1, n_rows=6000, n_steps=72, n_positives=120, plant_defects=False
    ).to_csv(raw, index=False)
    (tmp / "reports" / "sections").mkdir(parents=True)
    for name in ("01_problem", "07_limitations", "08_reproducibility"):
        (tmp / "reports" / "sections" / f"{name}.md").write_text(f"# {name}\n\nfixture section\n")
    cfg = tmp / "cfg.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "raw_csv": str(raw),
                    "processed_dir": str(tmp / "processed"),
                    "models_dir": str(tmp / "models"),
                    "reports_dir": str(tmp / "reports"),
                },
                "features": {"registry": str(reg)},
                "split": {"train_end_step": 48, "val_end_step": 60, "min_positives_per_split": 10},
                "review": {"review_period_steps": 24, "primary_k": 15, "k_grid": [5, 15, 30]},
                "selection": {"mi_k": 8, "l1_c": 0.5, "min_size": 4},
                "pca": {"n_components": 0.9},
                "tuning": {"tune_sample_rows": 3000, "n_iter": 2, "cv_folds": 2},
                "bootstrap": {"n_resamples": 5},
                "explain": {
                    "shap_background_rows": 100,
                    "shap_eval_rows": 200,
                    "n_local_examples": 2,
                    "pdp_top_features": 3,
                },
                "operating_point_path": str(tmp / "operating_point.yaml"),
            }
        )
    )
    return cfg, tmp


def _run(cfg: Path, *args: str) -> int:
    return main([*args, "--config", str(cfg)])


def test_full_chain_on_fixture(chain, monkeypatch) -> None:
    cfg, tmp = chain
    monkeypatch.chdir(tmp)  # model configs are read from configs/models relative to cwd
    import shutil

    (tmp / "configs").mkdir(exist_ok=True)
    shutil.copytree(tmp / "models_cfg", tmp / "configs" / "models", dirs_exist_ok=True)
    shutil.copy(
        Path(__file__).resolve().parents[1] / "configs" / "schema.yaml",
        tmp / "configs" / "schema.yaml",
    )
    assert _run(cfg, "validate-schema") == EXIT_OK
    assert _run(cfg, "profile") == EXIT_OK
    assert _run(cfg, "data-dictionary") == EXIT_OK
    assert _run(cfg, "split") == EXIT_OK
    for fs in ("primary", "strict_pretx"):
        assert _run(cfg, "build-features", "--feature-set", fs) == EXIT_OK
    assert _run(cfg, "eda") == EXIT_OK
    assert _run(cfg, "select-features") == EXIT_OK
    assert _run(cfg, "pca") == EXIT_OK
    assert (
        _run(
            cfg,
            "train",
            "--models",
            "dummy,logreg,hgb",
            "--feature-set",
            "primary",
            "--split",
            "val",
        )
        == EXIT_OK
    )
    assert _run(cfg, "compare", "--split", "val") == EXIT_OK
    assert _run(cfg, "tune", "--models", "logreg") == EXIT_OK
    assert (tmp / "configs" / "models" / "logreg.tuned.yaml").exists()
    assert _run(cfg, "choose-operating-point") == EXIT_OK
    assert _run(cfg, "freeze") == EXIT_OK
    assert _run(cfg, "evaluate", "--split", "test") == EXIT_OK
    assert _run(cfg, "select") == EXIT_OK
    assert _run(cfg, "reproduce-check") == EXIT_OK
    assert _run(cfg, "queue", "--period", "0") == EXIT_OK
    assert _run(cfg, "explain", "--model", "LATEST") == EXIT_OK
    assert _run(cfg, "fairness-availability") == EXIT_OK
    assert _run(cfg, "fairness") == EXIT_OK
    assert _run(cfg, "build-report") == EXIT_OK
    report = (tmp / "reports" / "final_report.md").read_text()
    assert DISCLAIMER in report[:2500]  # front matter
    assert report.rstrip().endswith(f"_{DISCLAIMER}_")  # single footer at the end
    assert "## 6. Bias & Fairness Analysis" in report
    state = json.loads((tmp / "processed" / "test_access.json").read_text())
    assert state["state"] == "evaluated" and state["reevaluations"] == []
    rep = json.loads((tmp / "reports" / "reproducibility.json").read_text())
    assert rep["exact"] is True
    assert (tmp / "reports" / "explainability.md").exists() and (
        tmp / "reports" / "bias_fairness_analysis.md"
    ).exists()
