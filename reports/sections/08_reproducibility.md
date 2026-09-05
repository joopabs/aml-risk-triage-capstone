# Reproducibility

## Environment

Python 3.11.12 (`.python-version`), dependencies pinned to exact versions in `requirements.txt`
(compiled from `requirements.in` with `uv`), development tooling in `requirements-dev.txt`. Global
seed 42 is set in `configs/base.yaml` and propagated to every splitter, sampler, estimator,
search, and SHAP sample. OMP threads 4, n_jobs 4.

## Commands (from a clean clone)

```bash
make setup                                  # venv, pinned deps, editable install, pre-commit hooks
make data                                   # fetch PaySim (Kaggle API token or manual), verify SHA-256
python -m aml_triage validate-schema        # V2: schema confirmed on 6,362,620 rows
python -m aml_triage profile                # reports/data_quality.*
python -m aml_triage data-dictionary
make pipeline                               # split -> features -> selection/PCA -> train -> compare -> tune
                                            # -> operating point -> freeze -> evaluate (single touch) -> select
                                            # -> reproduce-check -> explain -> fairness -> build-report
make test                                   # 115 tests incl. leakage, guard, vocabulary checks
make report && make slides
```

The test split may be scored once per configuration; a second `evaluate --split test` is refused
unless `--force-reevaluate --reason "..."` is given, and the reason is appended to
`data/processed/test_access.json`. A clean-clone rerun therefore records itself in that file.

## Measured tolerance (validation task V13)

`python -m aml_triage reproduce-check` refit the released candidate twice in fresh processes:
**exact** — maximum absolute
difference 0.00e+00 in per-row scores and 0.00e+00 against the released
bundle's validation metrics (`reports/reproducibility.json`).

## Artifacts and versions

| Artifact | Location |
|---|---|
| Released bundle | `models/20260904T225142-0dc8f82-hgb/` (`pipeline.sha256`, `config_snapshot.yaml`, `metrics.json`, `feature_list.json`, `model_card.md`); `models/LATEST` |
| Split manifest | `data/processed/split_manifest.json` (config hash `sha256:d099f2d0939d…`) |
| Test-access record | `data/processed/test_access.json` (state `evaluated`, first evaluated 2026-09-04T22:51:34+00:00, 0 re-evaluations, 1 audited re-freeze) |
| Fit-scope records | `data/processed/feature_pipeline_*.fitscope.json` (all `fitted_on: ["train"]`) |
| Operating point | `configs/operating_point.yaml` (chosen on validation, frozen 2026-09-04T22:22:38+00:00) |
| Tuned parameters | `configs/models/*.tuned.yaml`; search logs under `models/tuning/` |
| Data provenance | `data/README.md`, `configs/data_source.yaml` (SHA-256 verified on every fetch) |

Raw data, processed parquet files and `.joblib` binaries are never committed; `make pipeline`
regenerates them, and the bundle checksum lets a reviewer confirm an identical artifact.
