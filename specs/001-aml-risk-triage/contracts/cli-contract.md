# CLI Contract: `python -m aml_triage`

All commands accept `--config PATH` (default `configs/base.yaml`) and `--seed INT` (override).
Commands are idempotent given identical config and inputs. Exit codes: `0` success,
`2` validation/schema failure, `3` leakage or access-guard violation, `4` missing prerequisite
artifact, `1` other error. Every command logs the effective config hash and disclaimer.

| Command | Inputs | Outputs | Guards |
|---------|--------|---------|--------|
| `fetch-data` (wraps `scripts/fetch_data.sh`) | `configs/data_source.yaml`, optional Kaggle env | `data/raw/<file>.csv`; updates data_source.yaml on first download | refuses if `data/raw` tracked by git; sha256 mismatch → exit 2 |
| `validate-schema` | raw CSV, `configs/schema.yaml` | stdout summary | mismatch → exit 2 |
| `profile` | raw CSV | `reports/data_quality.md`, `reports/data_quality.json` | aggregates only; no row dumps |
| `data-dictionary` | schema + features registry | `reports/data_dictionary.md` | every feature needs rationale, else exit 2 |
| `split` | raw CSV, base config | `data/processed/{train,val,test}.parquet`, `split_manifest.json` | min positives per split, monotone step ranges → else exit 3; refuses if manifest frozen |
| `build-features --feature-set NAME` | splits, features registry | `data/processed/features_<set>_{train,val,test}.parquet` | strict_pretx must exclude batch_only |
| `eda` | train split (and raw for descriptive-only plots, labeled) | `reports/eda_summary.md`, `reports/figures/eda/*` | |
| `select-features` | train features | `reports/feature_selection.md`, updates `selected` set | fits on train only |
| `pca` | train features | `reports/pca_report.md`, figures | fits on train only |
| `train --models LIST --split val` | features, model configs | `models/runs/<candidate>/val_metrics.json`, predictions | `--split test` refused before freeze (exit 3) |
| `compare --split val` | run metrics | `reports/model_comparison.md` (val), curves | |
| `tune --models LIST` | train subsample, val | `configs/models/<id>.tuned.yaml`, search logs | reads train/val only |
| `choose-operating-point` | val predictions | `configs/operating_point.yaml` | must precede freeze |
| `freeze` | manifest, operating point | `data/processed/test_access.json` (frozen) | requires operating point present |
| `evaluate --split test` | frozen state, all candidates | test metrics with bootstrap CIs, predictions | one pass per config hash; repeat requires `--force-reevaluate --reason TEXT` (logged) |
| `select` | val + test metrics | `reports/selection_matrix.md`, `models/<version>/`, `models/LATEST` | exactly one selected |
| `reproduce-check` | selected config | tolerance record appended to README section | |
| `explain --model LATEST` | bundle, test predictions | `reports/explainability.md`, figures | seeded samples |
| `fairness-availability` | schema, raw column names | `reports/fairness_availability.json` | |
| `fairness` | availability record, test predictions | `reports/bias_fairness_analysis.md`, figures | label literal enforced |
| `build-report` | all section files | `reports/final_report.md` | missing section → exit 4 |
| `queue --period INDEX` | bundle, test features | `reports/review_queue_period_<i>.md` | prohibited fields absent |

Make targets: `setup`, `lint`, `test`, `data`, `pipeline` (split → build-features → select-features
→ pca → train → compare → tune → choose-operating-point → freeze → evaluate → select →
reproduce-check → explain → fairness-availability → fairness → build-report), `report`, `slides`,
`ci` (lint + test + smoke pipeline on `configs/smoke.yaml`), `api` (optional).
