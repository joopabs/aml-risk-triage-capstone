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
make pipeline EVALUATE_FLAGS='--force-reevaluate --reason "clean-clone reproducibility run"'
                                            # split -> features -> selection/PCA -> train -> compare -> tune
                                            # -> operating point -> freeze -> evaluate (audited) -> select
                                            # -> reproduce-check -> explain -> fairness -> build-report
make test                                   # 127 tests incl. leakage, guard, vocabulary checks
make report && make slides
```

The test split may be scored once per configuration; a second `evaluate --split test` is refused
unless `--force-reevaluate --reason "..."` is given, and the reason is appended to
`data/processed/test_access.json`. The split manifest and that record are tracked in git, so a
clean clone starts frozen and already evaluated: `split` and `freeze` verify that the recomputed
partition and operating point are identical to the sealed ones (and refuse otherwise), and the
`evaluate` flag above records the rerun in the audit trail.

## Clean-clone check (validation task SC-003, run 2026-09-06)

The commands above were executed in a fresh clone of the repository on the same machine
(Python 3.11.12, pinned requirements, PaySim re-downloaded and checksum-verified, license
re-confirmed as CC BY-SA 4.0 from the Kaggle API metadata). Outcome:

- Every one of the 301 metric values in the released bundle's `metrics.json` (validation and test,
  point estimates and bootstrap intervals, operating-point counts) reproduced exactly; only the four
  provenance fields (fit seconds and timestamps) differed.
- The clean-clone estimator and the released estimator produce identical scores on all 181,068
  validation rows (maximum absolute difference 0.0) and identical training curves.
- The temporal split, the selected feature set, the tuned hyperparameters, and the sealed operating
  point (threshold 0.971931, K = 200, cutoff 0.999977) were all regenerated identically. The
  Balanced Random Forest search's best cross-validation score differed only in the ninth decimal
  place (parallel summation order); its chosen parameters were identical.
- `pipeline.joblib` is not byte-identical across runs because the bundle embeds its version string
  and the operating point's `chosen_at` timestamp; `pipeline.sha256` therefore identifies one build,
  while equality of scores is the reproducibility criterion. No data, `.env`, or `.joblib` files are
  tracked; `detect-secrets` found nothing.

The check also surfaced a defect that this run fixed: the CI smoke pipeline had shared three tracked
paths with the real run and had overwritten the operating point file, the feature registry's
`selected` markers, and the README tolerance line with smoke values. The released bundle's
snapshots and the audit record still held the real values and no report or deck had used the smoke
values; the files were restored and every isolated configuration now refuses to write them.

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
regenerates them, and `reproduce-check` plus the clean-clone check above show that a regenerated
model scores identically to the released one.
