---
description: "Task list for Explainable AML Transaction-Risk Triage"
---

# Tasks: Explainable AML Transaction-Risk Triage

**Input**: Design documents from `specs/001-aml-risk-triage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md,
`.specify/memory/constitution.md` (v1.0.0)

**Tests**: Included. The spec requires automated tests (FR-043, FR-104) and the constitution makes
the leakage guard and vocabulary scan mandatory. Test tasks precede the code they guard where
practical.

**Organization**: Phases follow user-story priority from spec.md. Every task also carries its plan
milestone (M1–M9) so milestone-based tracking still works. No task contains implementation code.

**Validate-before-concluding rule**: any task whose output is prose about data or model results
(quality narrative, EDA summary, comparison discussion, fairness text, report sections, slides)
is sequenced strictly AFTER the task that produces the numbers, and its acceptance criteria
require citing the generated artifact. Placeholders `[PROFILE]`, `[VERIFY]`, `[MEASURED]` from
the spec are resolved only by those result-producing tasks (validation tasks V1–V13).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US7 from spec.md; Setup, Foundational, and Polish phases carry no story label
- Each task has sub-bullets: **Milestone / Type / Depends**, **Files**, **Accept**, **Verify**
- **Type** values: code, config, tests, notebooks, docs, reports, models, data, verification

## Path Conventions

Single Python package: `src/aml_triage/`, `tests/`, `configs/`, `notebooks/`, `data/`, `models/`,
`reports/`, `scripts/`, `deployment/`, `docs/` at repository root (see plan.md "Project Structure").

---

## Phase 1: Setup (Shared Infrastructure) — Milestone M1

**Purpose**: A clean clone installs, lints, and passes starter tests; disclaimer and configs exist
before any data is touched. Gates G3, G10 (partial), G2 (secret scan).

- [ ] T001 Create the repository directory skeleton with `.gitkeep` files per plan.md tree
  - Milestone M1 / Type: code / Depends: none
  - Files: `src/aml_triage/{utils,data,eda,features,models,evaluation,explain,fairness,reporting}/`, `tests/api/`, `notebooks/`, `configs/models/`, `data/{raw,processed}/`, `models/`, `reports/figures/{eda,features,models,explain,fairness}/`, `reports/slides/`, `scripts/`, `deployment/demo/`, `docs/`
  - Accept: every directory in the plan tree exists; `data/raw` and `data/processed` contain only `.gitkeep`
  - Verify: `find . -type d -not -path './.git*' | sort` matches plan tree

- [ ] T002 Write `pyproject.toml`, `.python-version`, and `LICENSE`
  - Milestone M1 / Type: code / Depends: T001
  - Files: `pyproject.toml` (package `aml_triage`, `requires-python = ">=3.11,<3.12"`, ruff, pytest, coverage ≥80% on `src/aml_triage`), `.python-version` (`3.11.12`), `LICENSE` (MIT, code only; data note)
  - Accept: `python --version` reports 3.11.12 inside the venv; `pip install -e .` succeeds
  - Verify: `python -c "import tomllib;tomllib.load(open('pyproject.toml','rb'))"`

- [ ] T003 [P] Author `requirements.in`, `requirements-dev.in`, `requirements-api.in` and compile pinned lockfiles
  - Milestone M1 / Type: code / Depends: T002
  - Files: `requirements.in` (pandas, numpy, scikit-learn, imbalanced-learn, shap, matplotlib, seaborn, joblib, pyarrow, pyyaml, pydantic), `requirements-dev.in` (pytest, pytest-cov, ruff, detect-secrets, pre-commit, nbstripout, jupyter, nbconvert, httpx), `requirements-api.in` (fastapi, uvicorn), `requirements.txt`, `requirements-dev.txt`, `requirements-api.txt`
  - Accept: every line in `requirements*.txt` has an exact `==` pin; XGBoost absent (research R-03)
  - Verify: `uv pip compile requirements.in -o requirements.txt && grep -vc '==' requirements.txt` returns 0 non-pinned package lines (comments excluded)

- [ ] T004 [P] Write `.gitignore` and `.env.example`
  - Milestone M1 / Type: code / Depends: T001
  - Files: `.gitignore` (`data/raw/`, `data/processed/`, `*.csv`, `*.parquet`, `.env`, `.venv/`, `models/**/*.joblib`, `.ipynb_checkpoints/`, `__pycache__/`, keep `.gitkeep`), `.env.example` (`KAGGLE_USERNAME=`, `KAGGLE_KEY=` placeholders only)
  - Accept: sample paths are ignored; `.gitkeep` files are not
  - Verify: `git check-ignore -q data/raw/x.csv data/processed/y.parquet .env models/v/pipeline.joblib && ! git check-ignore -q data/raw/.gitkeep`

- [ ] T005 [P] Configure pre-commit hooks and secret-scan baseline
  - Milestone M1 / Type: code / Depends: T003
  - Files: `.pre-commit-config.yaml` (ruff, ruff-format, detect-secrets with baseline, nbstripout), `.secrets.baseline`
  - Accept: `pre-commit install` succeeds; baseline generated from current tree with zero findings
  - Verify: `detect-secrets scan > .secrets.baseline && pre-commit run --all-files`

- [ ] T006 Write `Makefile` with targets `setup lint test data pipeline report slides ci api clean-derived`
  - Milestone M1 / Type: code / Depends: T003
  - Files: `Makefile` (sets `OMP_NUM_THREADS` from config; `pipeline` target runs the CLI sequence in contracts/cli-contract.md; `ci` fails if any `data/raw|processed` file is tracked)
  - Accept: `make -n <target>` prints the expected commands for every target
  - Verify: `make -n setup lint test ci pipeline | head -50`

- [ ] T007 [P] Create `configs/base.yaml`, `configs/vocabulary.yaml`, `configs/smoke.yaml` per contracts/config-schema.md
  - Milestone M1 / Type: config / Depends: T001
  - Files: `configs/base.yaml` (all profiling-dependent keys `null` with `# set after Vn` comments; `seed: 42`), `configs/vocabulary.yaml` (prohibited terms, allowlist, fairness-forbidden terms, `required_literal`, `scan_paths`), `configs/smoke.yaml` (small overrides for CI fixture run)
  - Accept: YAML parses; no non-null value for any key marked "set after Vn"
  - Verify: `python -c "import yaml;[yaml.safe_load(open(f)) for f in ['configs/base.yaml','configs/vocabulary.yaml','configs/smoke.yaml']]"`

- [ ] T008 Implement package constants and utilities
  - Milestone M1 / Type: code / Depends: T002
  - Files: `src/aml_triage/__init__.py`, `src/aml_triage/constants.py` (`DISCLAIMER` single string; `MODEL_OUTPUT_FIELDS`; `PROHIBITED_OUTPUT_FIELDS`), `src/aml_triage/utils/seed.py` (`set_global_seed`), `src/aml_triage/utils/io.py` (parquet/json/joblib helpers, `model_version()` = UTC timestamp + git short sha + candidate id, `sha256_file`), `src/aml_triage/utils/logging.py`
  - Accept: `DISCLAIMER` names synthetic data, educational use, human review, and the non-use list; `model_version()` matches `^\d{8}T\d{6}-[0-9a-f]{7}-\w+$`
  - Verify: `python -c "from aml_triage.constants import DISCLAIMER;assert 'synthetic' in DISCLAIMER.lower()"`

- [ ] T009 Implement config loader in `src/aml_triage/config.py`
  - Milestone M1 / Type: code / Depends: T007, T008
  - Files: `src/aml_triage/config.py` (pydantic models mirroring contracts/config-schema.md; unknown keys error; `require(keys)` helper that exits 2 on nulls; `config_hash()` over base+schema)
  - Accept: loading `configs/base.yaml` succeeds; an unknown key raises; `require(['review.primary_k'])` exits 2 while null
  - Verify: `python -c "from aml_triage.config import load;c=load('configs/base.yaml');print(c.config_hash())"`

- [ ] T010 Implement CLI skeleton in `src/aml_triage/cli.py` and `__main__.py`
  - Milestone M1 / Type: code / Depends: T009
  - Files: `src/aml_triage/cli.py`, `src/aml_triage/__main__.py` (register every command in contracts/cli-contract.md as a stub returning "not implemented" exit 1; shared `--config`, `--seed`; exit-code constants 0/1/2/3/4; logs config hash and disclaimer)
  - Accept: `--help` lists all 22 commands; stub exits 1 with a clear message
  - Verify: `python -m aml_triage --help | grep -c -E 'fetch-data|validate-schema|profile|split|build-features|train|freeze|evaluate|select|explain|fairness|build-report|queue'`

- [ ] T011 [P] Write test fixture and config tests
  - Milestone M1 / Type: tests / Depends: T009
  - Files: `tests/conftest.py` (small synthetic frame with the expected PaySim columns, several steps, a few positives, deliberate duplicates and one inconsistent balance; NOT PaySim rows), `tests/test_config.py`
  - Accept: fixture builds without data files; config tests cover load, unknown key, null-required
  - Verify: `pytest tests/test_config.py -q`

- [ ] T012 [P] Write vocabulary scan and optional-isolation tests
  - Milestone M1 / Type: tests / Depends: T007, T008
  - Files: `tests/test_vocabulary.py` (scans `configs/vocabulary.yaml` `scan_paths` for prohibited terms with allowlist; asserts disclaimer present in every `reports/*.md` when such files exist), `tests/test_core_without_optional.py` (imports every core module with `aml_triage.api` blocked via `sys.modules`)
  - Accept: both pass on the empty scaffold
  - Verify: `pytest tests/test_vocabulary.py tests/test_core_without_optional.py -q`

- [ ] T013 [P] Add GitHub Actions workflow `.github/workflows/ci.yml`
  - Milestone M1 / Type: code / Depends: T005, T006
  - Files: `.github/workflows/ci.yml` (ubuntu-latest, Python 3.11.12, `uv pip sync`, ruff, detect-secrets-hook, pytest with coverage, `make ci` smoke on fixture, tracked-data check; optional API job gated on `requirements-api.txt` changes)
  - Accept: workflow YAML valid; no dataset download in CI
  - Verify: `python -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'))"`

- [ ] T014 Write README and data README skeletons
  - Milestone M1 / Type: docs / Depends: T008
  - Files: `README.md` (title, purpose, disclaimer verbatim, synthetic-data notice, placeholder headings: Provenance, Setup, Commands, Repository Map, Results, Reproducibility Tolerance, Optional Steps, Links), `data/README.md` (Provenance, License, Checksum, Fetch, Synthetic Notice headings)
  - Accept: both files contain the word "synthetic" and the disclaimer; no results claimed
  - Verify: `grep -c synthetic README.md data/README.md`

- [ ] T015 Run the M1 checkpoint and fix until green
  - Milestone M1 / Type: verification / Depends: T001–T014
  - Files: none new
  - Accept: lint clean, all starter tests pass, pre-commit passes, git tracks no data
  - Verify: `make setup && make lint && make test && pre-commit run --all-files && ! git ls-files | grep -E '^data/(raw|processed)/.+\.(csv|parquet)$'`

**Checkpoint**: Scaffold green. Commit `chore: scaffold aml_triage package, configs, tooling, starter tests`.

---

## Phase 2: Foundational (Blocking Prerequisites) — Milestones M2, M3

**Purpose**: Data acquired with provenance, schema enforced, quality profiled, temporal split and
leakage-safe features built, EDA produced. No modeling story can start before this. Gates G2, G4, G5, G6 (partial).

**⚠️ CRITICAL**: T017 may STOP the project if the license does not permit educational use.

### Acquisition and schema (M2)

- [ ] T016 Write `configs/data_source.yaml` and `scripts/fetch_data.sh`
  - Milestone M2 / Type: code, config / Depends: T015
  - Files: `configs/data_source.yaml` (per contracts/artifacts-contract.md, nulls for sha256/dates/license), `scripts/fetch_data.sh` (Kaggle API path when `KAGGLE_*` env present; else print manual steps and wait; sha256 verify; refuse if `data/raw` tracked)
  - Accept: script exits 2 on checksum mismatch; prints manual instructions without credentials
  - Verify: `bash -n scripts/fetch_data.sh && KAGGLE_USERNAME= scripts/fetch_data.sh --dry-run`

- [ ] T017 Download PaySim and record provenance and license (validation task V1)
  - Milestone M2 / Type: data, docs / Depends: T016
  - Files: `data/raw/<filename>.csv` (local only), `configs/data_source.yaml` (fill `filename`, `sha256`, `downloaded_on`, `license_text_verbatim`, `license_verified_on`), `data/README.md` (Provenance, License, Checksum sections)
  - Accept: license text copied verbatim from the Kaggle page; if it does not permit educational use, STOP and record the blocker instead of proceeding; file not tracked by git
  - Verify: `shasum -a 256 data/raw/*.csv | grep -f <(yq '.sha256' configs/data_source.yaml) && git status --porcelain | grep -v data/raw`

- [ ] T018 Implement schema config, loader, and `validate-schema` command
  - Milestone M2 / Type: code, config / Depends: T017
  - Files: `configs/schema.yaml` (expected columns per contracts/config-schema.md), `src/aml_triage/data/load.py` (dtype map, category `type`), `src/aml_triage/data/schema.py` (presence, coercibility, nullability, allowed values; exit 2), `src/aml_triage/cli.py` (wire command)
  - Accept: missing column or bad dtype exits 2 with column named; success prints per-column summary
  - Verify: `python -m aml_triage validate-schema --config configs/base.yaml; echo exit=$?`

- [ ] T019 [P] Write `tests/test_schema.py`
  - Milestone M2 / Type: tests / Depends: T018
  - Files: `tests/test_schema.py` (fixture passes; dropped column → exit 2; string in numeric column → exit 2; identifiers flagged `role: identifier`)
  - Accept: all cases pass
  - Verify: `pytest tests/test_schema.py -q`

- [ ] T020 Reconcile `configs/schema.yaml` with the real file (validation task V2)
  - Milestone M2 / Type: verification, config / Depends: T018
  - Files: `configs/schema.yaml` (adjust to actual columns/dtypes), `data/README.md` (note any difference from expected)
  - Accept: `validate-schema` exits 0 on the real file; every deviation from research.md "expected" is written down
  - Verify: `python -m aml_triage validate-schema --config configs/base.yaml && echo OK`

### Profiling and dictionary (M2)

- [ ] T021 Implement profiling and the `profile` command
  - Milestone M2 / Type: code / Depends: T020
  - Files: `src/aml_triage/data/profiling.py` (row count; nulls per column; exact and near-duplicates; IQR and per-type quantile outliers; invalid values: negative/zero amounts, negative balances, balance-arithmetic inconsistency per type; class ratio overall, by type, by step; transactions per step; sensitive-attribute name scan; limitations template), `src/aml_triage/cli.py`
  - Accept: writes `reports/data_quality.md` and `.json` with aggregates only, no row dumps; disclaimer footer present
  - Verify: `python -m aml_triage profile --config configs/base.yaml && python -c "import json;d=json.load(open('reports/data_quality.json'));print(sorted(d))"`

- [ ] T022 Review profiling results and write the data-quality narrative (validation tasks V3, V4, V5, V6, V8)
  - Milestone M2 / Type: reports / Depends: T021
  - Files: `reports/data_quality.md` (narrative sections: findings, handling decision per finding with decision ids DQ-01…, source-data limitations, sensitive-attribute pre-scan result)
  - Accept: every number in the narrative is copied from `data_quality.json`; every finding has a handling decision (keep/correct/flag/exclude) with justification; text states whether positives exist in later steps and which types carry positives
  - Verify: `grep -c 'DQ-' reports/data_quality.md` ≥ number of findings; `pytest tests/test_vocabulary.py -q`

- [ ] T023 Implement data dictionary generator and `data-dictionary` command
  - Milestone M2 / Type: code / Depends: T020
  - Files: `src/aml_triage/data/dictionary.py` (raw columns from `configs/schema.yaml`; engineered rows from feature registry when present; exit 2 if a feature lacks rationale), `src/aml_triage/cli.py`
  - Accept: `reports/data_dictionary.md` lists every raw column with type, unit, range/values, description, prediction-time availability
  - Verify: `python -m aml_triage data-dictionary --config configs/base.yaml && grep -c '|' reports/data_dictionary.md`

- [ ] T024 [P] Create `notebooks/01_data_acquisition_and_schema.ipynb`
  - Milestone M2 / Type: notebooks / Depends: T021, T023
  - Files: `notebooks/01_data_acquisition_and_schema.ipynb` (header with disclaimer; imports `aml_triage`; calls schema validation and profiling; displays tables from `reports/`; no logic defined in cells)
  - Accept: runs top to bottom; outputs stripped by nbstripout on commit
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/01_data_acquisition_and_schema.ipynb --output /tmp/nb01.ipynb`

- [ ] T025 Fill profiling-dependent config values (validation tasks V4, V8, V9)
  - Milestone M3 / Type: config / Depends: T022
  - Files: `configs/base.yaml` (`review.review_period_steps`, `review.primary_k`, `review.k_grid`, `split.min_positives_per_split`, `split.train_end_step`, `split.val_end_step`, `tuning.tune_sample_rows`, `selection.min_size`), each with a comment citing the `data_quality.json` key that justified it
  - Accept: no nulls remain for split/review/tuning keys; chosen split bounds leave ≥ `min_positives_per_split` positives in each split according to positives-by-step in `data_quality.json`; K is a stated fraction of median transactions per review period
  - Verify: `python -c "from aml_triage.config import load;c=load('configs/base.yaml');c.require(['split.train_end_step','split.val_end_step','review.primary_k','review.review_period_steps'])"`

### Split and leakage guard (M3)

- [ ] T026 Implement temporal split and `split` command
  - Milestone M3 / Type: code / Depends: T025
  - Files: `src/aml_triage/data/split.py` (temporal by `step`; monotone ranges; min-positives guard exit 3; FR-041 stratified fallback with `fallback_reason`; excluded rows keyed by DQ decision id; writes `split_manifest.json` per contracts/artifacts-contract.md; refuses if manifest frozen), `src/aml_triage/cli.py`
  - Accept: parquet splits written; manifest fields complete; `config_hash` recorded
  - Verify: `python -m aml_triage split --config configs/base.yaml && python -c "import json;m=json.load(open('data/processed/split_manifest.json'));assert m['step_ranges']['train'][1]<m['step_ranges']['val'][0]<=m['step_ranges']['val'][1]<m['step_ranges']['test'][0]"`

- [ ] T027 [P] Write `tests/test_split.py`
  - Milestone M3 / Type: tests / Depends: T026
  - Files: `tests/test_split.py` (monotone ranges; disjoint indices; min-positives guard exits 3; fallback records reason; frozen manifest refuses re-split)
  - Accept: all pass on fixture
  - Verify: `pytest tests/test_split.py -q`

- [ ] T028 Author the feature registry and registry loader
  - Milestone M3 / Type: config, code / Depends: T022
  - Files: `configs/features.yaml` (candidate features from data-model.md §3 with `rationale`, `available_at_prediction_time`, `kind`, `sets`, `dictionary_entry`), `src/aml_triage/features/base.py` (load, validate uniqueness, assert `strict_pretx` contains no `batch_only` feature, exit 2 otherwise)
  - Accept: registry loads; `strict_pretx` validation passes; every entry has a one-line rationale
  - Verify: `python -c "from aml_triage.features.base import load_registry;r=load_registry('configs/features.yaml');print(len(r))"`

- [ ] T029 [P] Implement transaction-level feature transforms
  - Milestone M3 / Type: code / Depends: T028
  - Files: `src/aml_triage/features/transaction.py` (type one-hot, `log1p_amount`, amount buckets with training-fitted edges, origin/destination balance deltas, balance-inconsistency flags with tolerance, amount-to-origin-balance ratio with zero guard, zero-balance flags, step hour-of-day and day index)
  - Accept: each function is pure, vectorized, and referenced by name in `configs/features.yaml`
  - Verify: `python -c "import aml_triage.features.transaction as t;print([f for f in dir(t) if not f.startswith('_')])"`

- [ ] T030 [P] Implement causal prior-transaction aggregates
  - Milestone M3 / Type: code / Depends: T028
  - Files: `src/aml_triage/features/aggregates.py` (stable sort by `(step, row_index)`; groupby cumulative count/sum shifted by one per origin and destination; drops identifiers after use; documents same-step ordering limitation)
  - Accept: a row's aggregate never includes itself or any later row
  - Verify: covered by T031

- [ ] T031 [P] Write feature and causal-aggregate tests
  - Milestone M3 / Type: tests / Depends: T029, T030
  - Files: `tests/test_features.py` (transform shapes, zero guards, bucket edges fitted on train only), `tests/test_aggregates_causal.py` (brute-force O(n²) reference on fixture equals vectorized output; identifiers absent from output)
  - Accept: all pass
  - Verify: `pytest tests/test_features.py tests/test_aggregates_causal.py -q`

- [ ] T032 Implement pipeline builder, fit-scope wrapper, and `build-features` command
  - Milestone M3 / Type: code / Depends: T029, T030
  - Files: `src/aml_triage/features/pipeline.py` (`ColumnTransformer`/`Pipeline` per feature set; `FitScopeRecorder` wrapper that records which split ids were passed to `fit`; imblearn-compatible), `src/aml_triage/cli.py` (`build-features --feature-set`, writes `data/processed/features_<set>_{train,val,test}.parquet`)
  - Accept: fitting on train and transforming val/test succeeds; recorder shows `fitted_on == ["train"]`
  - Verify: `python -m aml_triage build-features --config configs/base.yaml --feature-set primary && ls data/processed/features_primary_*.parquet`

- [ ] T033 Write `tests/test_leakage.py` (FR-043)
  - Milestone M3 / Type: tests / Depends: T032
  - Files: `tests/test_leakage.py` (no test row index in train/val; step ranges monotone; `FitScopeRecorder` never saw val/test; resampled rows, if any, exist only in train fold; `strict_pretx` matrix has no batch-only columns)
  - Accept: all assertions pass on fixture; a deliberately leaked fixture variant fails
  - Verify: `pytest tests/test_leakage.py -q`

- [ ] T034 Run split and feature builds on the real data and inspect the manifest (validation task V9)
  - Milestone M3 / Type: verification, data / Depends: T026, T032, T033
  - Files: `data/processed/*` (local), `reports/data_quality.md` (append "Split summary" with figures copied from manifest)
  - Accept: positives per split ≥ minimum; strategy is temporal (or fallback documented with reason); both `primary` and `strict_pretx` matrices built
  - Verify: `python -m aml_triage build-features --config configs/base.yaml --feature-set strict_pretx && pytest tests/test_leakage.py tests/test_split.py -q`

### EDA (M3)

- [ ] T035 Implement EDA plots, figure styling, and `eda` command
  - Milestone M3 / Type: code / Depends: T034
  - Files: `src/aml_triage/reporting/figures.py` (consistent style, save helper adding caption + disclaimer), `src/aml_triage/eda/plots.py` (univariate distributions, class-conditional comparisons, correlation heatmap, positives over step, per-type amount distributions, 2-D scatter samples), `src/aml_triage/cli.py`
  - Accept: figures written to `reports/figures/eda/`; `reports/eda_summary.md` skeleton lists every figure with an empty "Observation" line; training split used for anything that could inform modeling
  - Verify: `python -m aml_triage eda --config configs/base.yaml && ls reports/figures/eda | wc -l`

- [ ] T036 Review EDA figures and write observations; append engineered rows to the data dictionary (validation tasks V5, V10)
  - Milestone M3 / Type: reports / Depends: T035
  - Files: `reports/eda_summary.md` (one observation per figure, written after viewing it; note which candidate features look informative and which post-transaction fields appear artifact-like), `reports/data_dictionary.md` (regenerated with engineered features)
  - Accept: no "Observation" line left empty; every claim references a figure filename
  - Verify: `! grep -q 'Observation: *$' reports/eda_summary.md && python -m aml_triage data-dictionary --config configs/base.yaml`

- [ ] T037 [P] Create notebooks 02 and 03
  - Milestone M3 / Type: notebooks / Depends: T036
  - Files: `notebooks/02_data_quality_and_eda.ipynb`, `notebooks/03_feature_engineering.ipynb` (call package functions; display registry, manifest, figures; no logic in cells)
  - Accept: both execute top to bottom from config
  - Verify: `for n in 02_data_quality_and_eda 03_feature_engineering; do jupyter nbconvert --to notebook --execute notebooks/$n.ipynb --output /tmp/$n.ipynb; done`

**Checkpoint**: Foundation ready. Commit in small groups (`data:`, `feat:`, `test:`, `docs:`).

---

## Phase 3: User Story 1 — Ranked review queue at fixed capacity (Priority: P1) 🎯 MVP — Milestones M4, M5, M6

**Goal**: Dummy baseline, random and rule comparators, and three candidates compared on
validation; tuned; operating point chosen on validation; single-touch test evaluation with
bootstrap CIs; selection matrix; persisted model bundle; top-K review queue for a period.

**Independent Test**: `python -m aml_triage evaluate --split test` then `select` and
`queue --period 0` produce Recall@K/Precision@K for every comparator and the selected model, and
the selected model beats random and dummy at the same K (SC-001), with the rule comparison shown
(SC-002). Every queue item carries score, rank, priority, model version, and disclaimer.

### Feature selection and PCA (M4)

- [ ] T038 [US1] Implement feature selection and `select-features` command
  - Milestone M4 / Type: code / Depends: T034
  - Files: `src/aml_triage/features/selection.py` (mutual-information filter `SelectKBest`; L1 logistic `SelectFromModel`; combine rule from config; both as pipeline steps fitted on train), `src/aml_triage/cli.py`
  - Accept: writes `reports/feature_selection.md` with before/after lists and scores for both methods; updates `selected` set in `configs/features.yaml`
  - Verify: `python -m aml_triage select-features --config configs/base.yaml && grep -c 'Before' reports/feature_selection.md`

- [ ] T039 [P] [US1] Implement PCA analysis and `pca` command
  - Milestone M4 / Type: code / Depends: T034
  - Files: `src/aml_triage/features/pca.py` (standardize numeric train features; fit PCA; scree and cumulative variance; 2-D label-colored projection on seeded sample; `pca_variant` set of top components), `src/aml_triage/cli.py`
  - Accept: `reports/pca_report.md` states the PCA role from config and lists explained variance; figures in `reports/figures/features/`
  - Verify: `python -m aml_triage pca --config configs/base.yaml && grep -i 'role' reports/pca_report.md`

- [ ] T040 [US1] Extend `tests/test_features.py` with selection and PCA fit-scope tests
  - Milestone M4 / Type: tests / Depends: T038, T039
  - Files: `tests/test_features.py`
  - Accept: selector and PCA `fit` recorded only on train; `strict_pretx` selection excludes batch-only features
  - Verify: `pytest tests/test_features.py -q -k "selection or pca"`

- [ ] T041 [US1] Review selection and PCA outputs and write the justification narratives
  - Milestone M4 / Type: reports / Depends: T038, T039
  - Files: `reports/feature_selection.md` (why the combined set was chosen; features dropped and why), `reports/pca_report.md` (whether components enter any model; why the selected model is expected to use raw features)
  - Accept: statements cite the tables generated in T038/T039; no metric claims about models
  - Verify: `pytest tests/test_vocabulary.py -q`

- [ ] T042 [P] [US1] Create `notebooks/04_feature_selection_and_pca.ipynb`
  - Milestone M4 / Type: notebooks / Depends: T041
  - Files: `notebooks/04_feature_selection_and_pca.ipynb`
  - Accept: executes top to bottom; displays reports and figures
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/04_feature_selection_and_pca.ipynb --output /tmp/nb04.ipynb`

### Candidates, metrics, capacity (M5)

- [ ] T043 [US1] Author model configs and the candidate registry
  - Milestone M5 / Type: config, code / Depends: T038
  - Files: `configs/models/dummy.yaml`, `configs/models/logreg.yaml`, `configs/models/balanced_rf.yaml`, `configs/models/hgb.yaml` (per contracts/config-schema.md; `random_state: ${seed}`; `imbalance_strategy`; `search_space`), `src/aml_triage/models/registry.py` (factory by dotted estimator path; optional XGBoost switch documented but off)
  - Accept: all four instantiate with the global seed; deep learning absent
  - Verify: `python -c "from aml_triage.models.registry import build;[build(i,42) for i in ['dummy','logreg','balanced_rf','hgb']]"`

- [ ] T044 [P] [US1] Implement ranking comparators
  - Milestone M5 / Type: code / Depends: T043
  - Files: `src/aml_triage/models/comparators.py` (`random_rank` seeded; `rule_rank`: rule-flag first then amount desc, or documented amount rule if flag absent per T020)
  - Accept: both return scores usable by capacity metrics; deterministic under seed
  - Verify: covered by T047

- [ ] T045 [P] [US1] Implement metric suite
  - Milestone M5 / Type: code / Depends: T032
  - Files: `src/aml_triage/evaluation/metrics.py` (PR-AUC via average precision, ROC-AUC, precision/recall/F1 at threshold, FPR, Brier, ECE 10 bins, confusion matrix, accuracy always paired with prevalence; `degenerate_scores` flag when score standard deviation is below `evaluation.degenerate_eps` or all scores are equal, reported next to PR-AUC)
  - Accept: output matches `MetricSet` in data-model.md §6 plus the `degenerate_scores` flag
  - Verify: covered by T047

- [ ] T046 [P] [US1] Implement capacity metrics and review-queue ranking
  - Milestone M5 / Type: code / Depends: T032
  - Files: `src/aml_triage/evaluation/capacity.py` (periods from `review_period_steps`; tie-break score desc, step asc, row index asc; `k_effective = min(K, n_rows)`; Recall@K null when zero positives and excluded from mean; pooled figure; `PeriodResult` records)
  - Accept: matches research R-10 definitions
  - Verify: covered by T047

- [ ] T047 [P] [US1] Write `tests/test_metrics.py` and `tests/test_capacity.py`
  - Milestone M5 / Type: tests / Depends: T044, T045, T046
  - Files: `tests/test_metrics.py` (known small vectors; accuracy carries prevalence; ECE bins; a constant-score vector sets `degenerate_scores` and Recall@K still computes), `tests/test_capacity.py` (ties resolved deterministically; period shorter than K reports shortfall; zero-positive period excluded from mean; comparators deterministic)
  - Accept: all pass
  - Verify: `pytest tests/test_metrics.py tests/test_capacity.py -q`

- [ ] T048 [US1] Implement training and the `train` command with test-split guard
  - Milestone M5 / Type: code / Depends: T043, T045, T046
  - Files: `src/aml_triage/models/train.py` (fit pipeline+estimator on train for a feature set; predict val; save predictions parquet and `models/runs/<candidate>/val_metrics.json`), `src/aml_triage/cli.py` (`--split test` exits 3 unless `test_access.json` state is `frozen`)
  - Accept: val metrics written for every candidate; test refused before freeze
  - Verify: `python -m aml_triage train --config configs/base.yaml --models hgb --split test; test $? -eq 3`

- [ ] T049 [US1] Implement calibration assessment, comparison tables, and `compare` command
  - Milestone M5 / Type: code / Depends: T048
  - Files: `src/aml_triage/evaluation/calibration.py` (reliability curve, Brier, ECE; isotonic-on-validation helper with PR-AUC-drop tolerance), `src/aml_triage/evaluation/compare.py` (tables per contracts; PR/ROC/calibration curves; accuracy last with prevalence), `src/aml_triage/reporting/tables.py` (markdown writer with disclaimer footer), `src/aml_triage/cli.py`
  - Accept: `reports/model_comparison.md` validation section contains all candidates and comparators at every K in `k_grid`
  - Verify: `python -m aml_triage compare --config configs/base.yaml --split val && grep -c 'recall_at_k\|Recall@K' reports/model_comparison.md`

- [ ] T050 [US1] Run validation training and comparison for all candidates on `primary` and `strict_pretx`; write the validation discussion
  - Milestone M5 / Type: models, reports / Depends: T047, T049
  - Files: `models/runs/*/val_metrics.json`, `reports/model_comparison.md` (validation discussion written after tables exist; ablation gap between feature sets discussed as simulator-artifact evidence per research R-06)
  - Accept: discussion cites table values; no test numbers appear; accuracy not headlined
  - Verify: `python -m aml_triage train --config configs/base.yaml --models dummy,logreg,balanced_rf,hgb --split val && python -m aml_triage compare --config configs/base.yaml --split val && pytest tests/test_vocabulary.py -q`

- [ ] T051 [P] [US1] Create `notebooks/05_model_comparison_validation.ipynb`
  - Milestone M5 / Type: notebooks / Depends: T050
  - Files: `notebooks/05_model_comparison_validation.ipynb`
  - Accept: executes; shows validation tables and curves only
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/05_model_comparison_validation.ipynb --output /tmp/nb05.ipynb`

### Tuning, operating point, single-touch test, selection (M6)

- [ ] T052 [US1] Implement tuning and the `tune` command
  - Milestone M6 / Type: code / Depends: T050
  - Files: `src/aml_triage/models/tune.py` (seeded stratified subsample of train of `tune_sample_rows`; `RandomizedSearchCV` with `average_precision`, folds within subsample; refit best on full train; score on val; write `configs/models/<id>.tuned.yaml` and search log), `src/aml_triage/cli.py`
  - Accept: tuned configs written for logreg, balanced_rf, hgb; wall-clock recorded
  - Verify: `python -m aml_triage tune --config configs/base.yaml --models logreg,balanced_rf,hgb && ls configs/models/*.tuned.yaml`

- [ ] T053 [US1] Implement operating-point selection and `choose-operating-point` command
  - Milestone M6 / Type: code / Depends: T052
  - Files: `src/aml_triage/evaluation/threshold.py` (F2-max threshold on validation; isotonic decision per calibration tolerance; `priority_rule` per data-model.md §8 and `k_score_cutoff` = score of the K-th ranked validation transaction; writes `configs/operating_point.yaml` with `chosen_on: val`), `src/aml_triage/cli.py`
  - Accept: file written with primary K, threshold, priority rule, k_score_cutoff, calibration decision and log
  - Verify: `python -m aml_triage choose-operating-point --config configs/base.yaml && cat configs/operating_point.yaml`

- [ ] T054 [US1] Implement `freeze`, test-access guard, bootstrap CIs, and `evaluate --split test`
  - Milestone M6 / Type: code / Depends: T053
  - Files: `src/aml_triage/cli.py` (`freeze` writes `data/processed/test_access.json` state `frozen`, requires operating point; `evaluate --split test` allowed once per config hash, else exit 3 unless `--force-reevaluate --reason`, reason appended to `reevaluations` and to the report), `src/aml_triage/evaluation/bootstrap.py` (row-resample test for PR-AUC and Recall@K CIs, `n_resamples` from config)
  - Accept: state machine `locked → frozen → evaluated` per data-model.md §9
  - Verify: covered by T055 and T056

- [ ] T055 [US1] Extend `tests/test_leakage.py` with test-access guard tests
  - Milestone M6 / Type: tests / Depends: T054
  - Files: `tests/test_leakage.py` (train/evaluate on test exits 3 when locked; second evaluate exits 3 without reason; reason recorded when forced; freeze refused without operating point)
  - Accept: all pass
  - Verify: `pytest tests/test_leakage.py -q`

- [ ] T056 [US1] Run tune → choose-operating-point → freeze → evaluate test once on the real data; confirm the guard
  - Milestone M6 / Type: models, verification / Depends: T055
  - Files: `data/processed/test_access.json`, `models/runs/*/test_metrics.json` (local), `reports/model_comparison.md` (test tables appended by tool)
  - Accept: one successful test evaluation with CIs for all candidates and comparators; an immediate second run exits 3
  - Verify: `python -m aml_triage freeze --config configs/base.yaml && python -m aml_triage evaluate --config configs/base.yaml --split test && python -m aml_triage evaluate --config configs/base.yaml --split test; test $? -eq 3`

- [ ] T057 [US1] Implement selection matrix, model bundle persistence, and `select` command
  - Milestone M6 / Type: code / Depends: T056
  - Files: `src/aml_triage/evaluation/compare.py` (selection matrix columns per data-model.md §10; exactly one `selected`), `src/aml_triage/utils/io.py` (bundle writer: `pipeline.joblib` + `pipeline.sha256`, `config_snapshot.yaml`, `metrics.json`, `feature_list.json`, `model_card.md` template with required sections, `models/LATEST`), `src/aml_triage/cli.py`
  - Accept: `models/<version>/` complete; `models/LATEST` points to it; selection uses validation numbers, reporting uses test numbers
  - Verify: `python -m aml_triage select --config configs/base.yaml && ls models/$(cat models/LATEST)`

- [ ] T058 [US1] Implement `queue --period` command
  - Milestone M6 / Type: code / Depends: T057
  - Files: `src/aml_triage/cli.py`, `src/aml_triage/evaluation/capacity.py` (queue writer with only permitted columns: rank, row_index, step, type, risk_score, review_priority, model_version; `review_priority` derived by the `priority_rule` in `configs/operating_point.yaml`; disclaimer footer; shortfall note if `n_rows < K`)
  - Accept: `reports/review_queue_period_<i>.md` has exactly the permitted columns; every rank ≤ K is `high`
  - Verify: `python -m aml_triage queue --config configs/base.yaml --period 0 && head -5 reports/review_queue_period_0.md`

- [ ] T059 [US1] Write the selection, capacity, and model-card narratives from the test results
  - Milestone M6 / Type: reports, models / Depends: T057, T058
  - Files: `reports/selection_matrix.md` (verdict reasoning across all matrix columns), `reports/capacity_analysis.md` (Recall@K and Precision@K vs K, per-period distribution, FP/FN trade-off narrative, illustrative KPI counts vs random and rule, labeled "illustrative"), `reports/model_comparison.md` (test discussion incl. validation-vs-test shift), `models/<version>/model_card.md` (intended use, non-use, limitations, metrics)
  - Accept: SC-001 and SC-002 evaluated explicitly with numbers copied from `metrics.json`; if the selected model does not beat the rule baseline, that is stated; no currency figures
  - Verify: `grep -c illustrative reports/capacity_analysis.md && pytest tests/test_vocabulary.py -q`

- [ ] T060 [P] [US1] Create `notebooks/06_tuning_capacity_and_test.ipynb`
  - Milestone M6 / Type: notebooks / Depends: T059
  - Files: `notebooks/06_tuning_capacity_and_test.ipynb` (reads saved metrics; does not call `evaluate --split test`)
  - Accept: executes without triggering test re-evaluation
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/06_tuning_capacity_and_test.ipynb --output /tmp/nb06.ipynb && python -c "import json;print(json.load(open('data/processed/test_access.json'))['reevaluations'])"` prints `[]`

**Checkpoint**: US1 complete. The MVP delivers a ranked queue evaluated at capacity with a persisted model.

---

## Phase 4: User Story 2 — Reproducible end-to-end pipeline (Priority: P2) — Milestones M6, M1

**Goal**: A peer regenerates every metric and figure from a clean clone with README commands;
tolerance measured, not assumed; CI smoke passes; coverage ≥80%.

**Independent Test**: Fresh environment in a scratch directory, `make setup && make data &&
make pipeline && make report`, then diff metrics against committed values (SC-003); `pytest`
passes (SC-004); no data or secrets tracked (SC-005).

- [ ] T061 [US2] Implement `reproduce-check` command
  - Milestone M6 / Type: code / Depends: T057
  - Files: `src/aml_triage/cli.py` (refit the selected candidate twice with identical config; diff `metrics.json`; write `reports/reproducibility.json` with max absolute difference per metric), `README.md` (Reproducibility Tolerance section populated by the command or by hand from the JSON)
  - Accept: command exits 0 and records tolerance (target 0.0)
  - Verify: `python -m aml_triage reproduce-check --config configs/base.yaml && cat reports/reproducibility.json`

- [ ] T062 [US2] Run reproduce-check and record the tolerance (validation task V13)
  - Milestone M6 / Type: verification, docs / Depends: T061
  - Files: `README.md` (tolerance value and, if non-zero, the thread-count decision from research R-13)
  - Accept: README states the measured tolerance; if non-zero, `compute.n_jobs`/`omp_num_threads` were revisited and the outcome recorded
  - Verify: `grep -A3 'Reproducibility Tolerance' README.md`

- [ ] T063 [P] [US2] Implement the CI smoke sample and `make ci`
  - Milestone M1 / Type: code / Depends: T057
  - Files: `scripts/make_sample.py` (writes a seeded synthetic sample shaped like the schema from the test fixture generator, not from PaySim), `configs/smoke.yaml` (paths to sample; tiny K; small `n_iter`; `n_resamples` small), `Makefile` (`ci` target), `.github/workflows/ci.yml` (run `make ci`)
  - Accept: `make ci` completes the full CLI sequence on the sample in under 10 minutes with no dataset download
  - Verify: `time make ci`

- [ ] T064 [US2] Complete README setup, commands, and repository map sections
  - Milestone M8 / Type: docs / Depends: T062
  - Files: `README.md` (ordered commands: setup, data fetch incl. manual path, pipeline, tests, report, slides; repository map; provenance summary linking `data/README.md`)
  - Accept: every command in README exists as a Make target or CLI command in contracts/cli-contract.md
  - Verify: `grep -oE 'make [a-z-]+' README.md | sort -u | while read -r m t; do make -n $t >/dev/null || echo "missing $t"; done`

- [ ] T065 [US2] Perform the clean-clone reproducibility run (SC-003, SC-005)
  - Milestone M6 / Type: verification / Depends: T063, T064
  - Files: none committed; scratch clone under the session scratchpad directory
  - Accept: pipeline and report regenerate from README commands alone; `git diff --stat reports/*.md models/*/metrics.json` shows no metric changes (or within recorded tolerance); `git ls-files` shows no data, `.env`, or joblib files; `detect-secrets scan` finds nothing new
  - Verify: `git clone . "$SCRATCH/clone" && cd "$SCRATCH/clone" && make setup && make data && make pipeline && make report && git status --porcelain`

- [ ] T066 [US2] Raise test coverage to ≥80% on `src/aml_triage`
  - Milestone M1 / Type: tests / Depends: T060
  - Files: `tests/*.py` (fill gaps reported by coverage; no test reads real data)
  - Accept: coverage gate in `pyproject.toml` passes
  - Verify: `pytest --cov=aml_triage --cov-fail-under=80 -q`

**Checkpoint**: US2 complete. Commit `test: reproducibility check, CI smoke, coverage gate`.

---

## Phase 5: User Story 3 — Explain why a transaction was prioritized (Priority: P3) — Milestone M7

**Goal**: SHAP global and ≥3 local explanations for the selected model, PDP/ICE with validity
checks or documented alternatives, plain-language captions, consistency discussion.

**Independent Test**: `python -m aml_triage explain --model LATEST` produces
`reports/explainability.md` and figures; each local explanation carries a caption and the
disclaimer; each top feature has a PDP/ICE figure or a stated reason and alternative (SC-008).

- [ ] T067 [US3] Implement SHAP global and local explanations
  - Milestone M7 / Type: code / Depends: T057
  - Files: `src/aml_triage/explain/shap_reports.py` (explainer chosen by estimator type; seeded train background of `shap_background_rows`; seeded test sample of `shap_eval_rows`; summary and mean-|SHAP| bar; local waterfalls for `n_local_examples` top-K rows from period 0)
  - Accept: figures saved under `reports/figures/explain/`; feature names match `feature_list.json`
  - Verify: covered by T070

- [ ] T068 [P] [US3] Implement PDP/ICE with validity checks
  - Milestone M7 / Type: code / Depends: T057
  - Files: `src/aml_triage/explain/pdp_ice.py` (top features from SHAP; correlation check against other top features with threshold; status `produced`/`omitted` with reason; permutation importance as documented alternative)
  - Accept: returns `pdp_ice` records per data-model.md §12
  - Verify: covered by T070

- [ ] T069 [P] [US3] Implement plain-language captions
  - Milestone M7 / Type: code / Depends: T008
  - Files: `src/aml_triage/explain/captions.py` (template sentences per feature from registry `rationale`; direction words "raised/lowered the risk score"; never determination words; appends disclaimer)
  - Accept: captions contain no term from `configs/vocabulary.yaml` prohibited list
  - Verify: `pytest tests/test_vocabulary.py -q`

- [ ] T070 [US3] Implement the `explain` command
  - Milestone M7 / Type: code / Depends: T067, T068, T069
  - Files: `src/aml_triage/cli.py` (`explain --model LATEST`; writes `reports/explainability.md` with sections Global, Local Examples, PDP/ICE Validity, Consistency Notes (empty placeholder to be filled in T071), disclaimer)
  - Accept: command runs against `models/LATEST` and saved test predictions only
  - Verify: `python -m aml_triage explain --config configs/base.yaml --model LATEST && ls reports/figures/explain | wc -l`

- [ ] T071 [US3] Review attributions against EDA and write the consistency discussion
  - Milestone M7 / Type: reports / Depends: T070
  - Files: `reports/explainability.md` (Consistency Notes: agreement or surprise per top feature referencing `reports/eda_summary.md` figures; plain-language summary for business audience; explicit note on any post-transaction feature dominance as artifact evidence)
  - Accept: every top feature discussed; surprises not omitted; no empty section
  - Verify: `! grep -q 'TODO' reports/explainability.md && pytest tests/test_vocabulary.py -q`

- [ ] T072 [US3] Create `notebooks/07_explainability_and_fairness.ipynb` (explainability section)
  - Milestone M7 / Type: notebooks / Depends: T071
  - Files: `notebooks/07_explainability_and_fairness.ipynb` (header, explainability cells; fairness section added in T079)
  - Accept: executes; displays saved figures
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/07_explainability_and_fairness.ipynb --output /tmp/nb07.ipynb`

**Checkpoint**: US3 complete.

---

## Phase 6: User Story 4 — Ethical AI, fairness-data check, and limitations (Priority: P4) — Milestone M7

**Goal**: Sensitive-attribute availability record; demographic metrics if valid labels exist,
otherwise an explicit non-measurability statement plus an operational error-slice analysis
labeled exactly as such; limitations; mitigations; governance audit plan.

**Independent Test**: `reports/bias_fairness_analysis.md` has the six required headings in order,
the availability record, the correct branch, and the literal label; `tests/test_vocabulary.py`
passes its fairness assertions (SC-009).

- [ ] T073 [US4] Implement the availability check and `fairness-availability` command
  - Milestone M7 / Type: code / Depends: T020
  - Files: `src/aml_triage/fairness/availability.py` (fixed attribute list; proxy name scan from `configs/schema.yaml`; evidence strings; `any_valid_label`), `src/aml_triage/cli.py` (writes `reports/fairness_availability.json`)
  - Accept: record conforms to contracts/artifacts-contract.md; result is derived from actual columns, not assumed
  - Verify: `python -m aml_triage fairness-availability --config configs/base.yaml && cat reports/fairness_availability.json`

- [ ] T074 [P] [US4] Implement operational error-slice analysis
  - Milestone M7 / Type: code / Depends: T057
  - Files: `src/aml_triage/fairness/slices.py` (slices from config: type, amount band, origin-balance band, step band; per-slice n, prevalence, Recall@K, Precision@K, FPR, FNR, Brier; `label` fixed to the config literal)
  - Accept: output conforms to data-model.md §14; band edges computed from training split
  - Verify: covered by T076

- [ ] T075 [P] [US4] Implement demographic fairness metrics (conditional path)
  - Milestone M7 / Type: code / Depends: T057
  - Files: `src/aml_triage/fairness/demographic.py` (demographic parity difference, equalized odds difference, disparate impact ratio; executed only when `any_valid_label` is true; unit-tested on fixture with a synthetic group column)
  - Accept: correct on hand-computed fixture values
  - Verify: `pytest tests/test_fairness.py -q` (add file in this task)

- [ ] T076 [US4] Implement the `fairness` command and report writer
  - Milestone M7 / Type: code / Depends: T073, T074, T075
  - Files: `src/aml_triage/cli.py`, `src/aml_triage/fairness/report.py` (writes `reports/bias_fairness_analysis.md` with headings in order: Sensitive-Attribute Availability Record; Demographic Fairness; Operational Error-Slice Analysis; Limitations; Mitigations; Governance-Controlled Fairness Audit Plan; branch text per contracts; figures to `reports/figures/fairness/`; prose sections left as marked placeholders for T078)
  - Accept: headings present and ordered; non-measurability sentence present when `any_valid_label` is false
  - Verify: `python -m aml_triage fairness --config configs/base.yaml && grep -n '^## ' reports/bias_fairness_analysis.md`

- [ ] T077 [US4] Extend `tests/test_vocabulary.py` with fairness-labeling assertions
  - Milestone M7 / Type: tests / Depends: T076
  - Files: `tests/test_vocabulary.py` (when `fairness_availability.json.any_valid_label` is false: report must contain `required_literal`, must not contain any `fairness_forbidden_when_unavailable` term; heading order check)
  - Accept: passes on generated report; fails on a fixture report that mislabels slices
  - Verify: `pytest tests/test_vocabulary.py -q`

- [ ] T078 [US4] Review slice results and write Limitations, Mitigations, and the Governance Audit Plan
  - Milestone M7 / Type: reports / Depends: T077
  - Files: `reports/bias_fairness_analysis.md` (Limitations: imbalance handling, leakage controls, overfitting evidence from val-vs-test, synthetic-label validity, simulator artifacts, non-transferability, and the sentence that results cannot establish real AML effectiveness, fairness, or regulatory suitability; Mitigations: concrete and feasible; Audit Plan: data, metrics, owners, cadence)
  - Accept: slice observations cite the generated tables; no operational slice described with protected-group language; placeholders removed
  - Verify: `! grep -q 'PLACEHOLDER' reports/bias_fairness_analysis.md && pytest tests/test_vocabulary.py -q`

- [ ] T079 [US4] Append the fairness section to `notebooks/07_explainability_and_fairness.ipynb`
  - Milestone M7 / Type: notebooks / Depends: T078
  - Files: `notebooks/07_explainability_and_fairness.ipynb`
  - Accept: executes; displays availability record and slice tables
  - Verify: `jupyter nbconvert --to notebook --execute notebooks/07_explainability_and_fairness.ipynb --output /tmp/nb07.ipynb`

**Checkpoint**: US4 complete.

---

## Phase 7: User Story 5 — Communicate to two audiences (Priority: P5) — Milestone M8

**Goal**: Final report assembled from generated sections and exported; technical deck via
nbconvert slides; business deck from a committed outline; both 8–12 slides; README results.

**Independent Test**: `scripts/check_slide_counts.py` passes for both decks; `final_report.md`
contains §1–§8; vocabulary test passes on all prose (SC-011).

- [ ] T080 [US5] Implement the report builder and `build-report` command
  - Milestone M8 / Type: code / Depends: T059, T071, T078
  - Files: `src/aml_triage/reporting/report_builder.py` (assembles `reports/final_report.md` from front matter + §1 Problem, §2 Data and Dictionary, §3 EDA + FE, §4 Models and Selection, §5 Explainability, §6 Bias & Fairness Analysis, §7 Limitations, §8 Reproducibility; exit 4 on any missing section file), `src/aml_triage/cli.py`
  - Accept: exit 4 when a section is missing; success writes the full report with disclaimer front matter
  - Verify: `python -m aml_triage build-report --config configs/base.yaml; echo exit=$?`

- [ ] T081 [P] [US5] Write export and slide-count scripts
  - Milestone M8 / Type: code / Depends: T001
  - Files: `scripts/export_report.sh` (pandoc if present; else documented fallback message per research R-11), `scripts/check_slide_counts.py` (counts reveal.js sections in HTML and slides in PPTX; exits 1 unless 8 ≤ n ≤ 12; `--dump-text` mode writes `.pptx` slide text to `reports/slides/business_deck.txt` so the vocabulary scan covers the deck)
  - Accept: script rejects a 7-slide and a 13-slide fixture
  - Verify: `python scripts/check_slide_counts.py --self-test`

- [ ] T082 [US5] Write the hand-authored report sections
  - Milestone M8 / Type: reports / Depends: T080
  - Files: `reports/sections/01_problem.md` (from spec Business Context; K stated; KPI labeled illustrative; human review workflow, investigator role, and override capability described per FR-083), `reports/sections/07_limitations.md` (consolidates data-quality, model, fairness limitations), `reports/sections/08_reproducibility.md` (commands, seed, tolerance, artifact versions)
  - Accept: every number cites a generated artifact; no currency; disclaimer present; FR-083 workflow paragraph present in §1
  - Verify: `python -m aml_triage build-report --config configs/base.yaml && grep -qi 'override' reports/final_report.md && pytest tests/test_vocabulary.py -q`

- [ ] T083 [US5] Build and export the final report
  - Milestone M8 / Type: reports, verification / Depends: T081, T082
  - Files: `reports/final_report.md`, `reports/final_report.pdf`
  - Accept: PDF opens; §1–§8 present; table of contents matches spec FR-090
  - Verify: `scripts/export_report.sh && grep -c '^## ' reports/final_report.md`

- [ ] T084 [US5] Create the technical deck notebook and export slides
  - Milestone M8 / Type: notebooks, reports / Depends: T083
  - Files: `notebooks/90_technical_deck.ipynb` (8–12 slides: framing, data, quality, features and split, comparison, selection, capacity, explainability, fairness, reproducibility, next steps; title and closing slides carry disclaimer), `reports/slides/technical_deck.html`, `reports/slides/technical_deck.pdf`
  - Accept: slide count within range; every metric slide cites `metrics.json` values
  - Verify: `jupyter nbconvert notebooks/90_technical_deck.ipynb --to slides --output-dir reports/slides --output technical_deck && python scripts/check_slide_counts.py reports/slides/technical_deck.html`

- [ ] T085 [P] [US5] Write the business deck outline
  - Milestone M8 / Type: docs / Depends: T083
  - Files: `reports/slides/business_deck_outline.md` (8–12 slides: problem, what the tool does and does not do, investigator workflow and override, illustrative KPI vs random and rule, risks, governance and human-in-the-loop, what real deployment would require, next steps; no unexplained technical terms; every number prefixed "illustrative")
  - Accept: `grep -c illustrative` ≥ number of numeric claims; non-use list present
  - Verify: `pytest tests/test_vocabulary.py -q && grep -c illustrative reports/slides/business_deck_outline.md`

- [ ] T086 [US5] Build the business deck from the outline and export
  - Milestone M8 / Type: reports / Depends: T085
  - Files: `reports/slides/business_deck.pptx`, `reports/slides/business_deck.pdf` (authored in PowerPoint, Canva, or Google Slides; manual step)
  - Accept: content matches outline; disclaimer on title and closing slides; dumped text passes the vocabulary scan
  - Verify: `python scripts/check_slide_counts.py reports/slides/business_deck.pptx --dump-text && pytest tests/test_vocabulary.py -q`

- [ ] T087 [US5] Verify both decks and the report together
  - Milestone M8 / Type: verification / Depends: T084, T086
  - Files: none new
  - Accept: both decks 8–12 slides; report PDF present; vocabulary scan clean
  - Verify: `python scripts/check_slide_counts.py reports/slides/technical_deck.html reports/slides/business_deck.pptx && test -f reports/final_report.pdf && pytest tests/test_vocabulary.py -q`

- [ ] T088 [US5] Complete README results and links
  - Milestone M8 / Type: docs / Depends: T087
  - Files: `README.md` (Results: primary PR-AUC and Recall@K with CIs copied from `models/<LATEST>/metrics.json`, comparators, "illustrative" KPI; Links: report, decks, model card; Optional Steps: status "not attempted" until Phase 8/9 change it)
  - Accept: numbers match `metrics.json`; disclaimer present; no accuracy headline
  - Verify: `grep -E 'PR-AUC|Recall@K' README.md && pytest tests/test_vocabulary.py -q`

**Checkpoint**: Core deliverables complete (Steps 1–7). Gates G1–G11 evidenced. Only now may Phase 8–9 begin.

---

## Phase 8: User Story 6 — Optional local scoring demo (Priority: P6, optional Step 8) — Milestone M9

**Goal**: Local FastAPI service reusing `models/LATEST`; validation errors on bad input; no
decision field; deployment guide, Docker image, demo recording.

**Independent Test**: Service answers `/health` and `/score` per contracts/scoring-api.yaml;
invalid payload returns 422; `tests/api` passes; core tests pass with the API package absent.

- [ ] T089 [US6] Implement API schemas from the OpenAPI contract
  - Milestone M9 / Type: code / Depends: T088
  - Files: `src/aml_triage/api/__init__.py`, `src/aml_triage/api/schemas.py` (pydantic models mirroring `TransactionRequest` and `ScoreResponse`; `extra="forbid"`; no allow/block/decision fields)
  - Accept: generated OpenAPI matches contracts/scoring-api.yaml field-for-field
  - Verify: covered by T091

- [ ] T090 [US6] Implement the scoring service and app
  - Milestone M9 / Type: code / Depends: T089
  - Files: `src/aml_triage/api/service.py` (load `models/LATEST` bundle once; build feature row; derive `review_priority` with the score-only bands from `configs/operating_point.yaml` (high if score ≥ `k_score_cutoff`, medium if ≥ threshold, low otherwise); top contributing features via SHAP or coefficients; never logs request bodies), `src/aml_triage/api/main.py` (`GET /health`, `POST /score`; disclaimer in every response)
  - Accept: service starts with `uvicorn aml_triage.api.main:app`
  - Verify: `uvicorn aml_triage.api.main:app --port 8000 & sleep 3; curl -s localhost:8000/health; kill %1`

- [ ] T091 [US6] Write `tests/api/test_scoring_api.py`
  - Milestone M9 / Type: tests / Depends: T090
  - Files: `tests/api/test_scoring_api.py` (skip if fastapi missing; health fields; score fields exactly per contract; 422 on missing field; 422 on unknown extra field; no prohibited output field; disclaimer present)
  - Accept: all pass
  - Verify: `pytest tests/api -q`

- [ ] T092 [US6] Run the demo end to end and re-verify core isolation
  - Milestone M9 / Type: verification / Depends: T091
  - Files: none new
  - Accept: example request from `specs/001-aml-risk-triage/contracts/examples/score_request.json` returns the four required fields; core tests pass with `aml_triage.api` blocked
  - Verify: `curl -s -X POST localhost:8000/score -H 'content-type: application/json' -d @specs/001-aml-risk-triage/contracts/examples/score_request.json && pytest tests/test_core_without_optional.py -q`

- [ ] T093 [P] [US6] Write Dockerfile and deployment guide
  - Milestone M9 / Type: code, docs / Depends: T090
  - Files: `deployment/Dockerfile` (copies `src/`, `configs/`, selected `models/<version>/` only; no `data/`), `deployment/DEPLOYMENT.md` (run locally, run container, config, model version, rollback via `models/LATEST`, limits and disclaimer)
  - Accept: image builds and answers `/health`
  - Verify: `docker build -t aml-triage-api -f deployment/Dockerfile . && docker run --rm -d -p 8000:8000 --name aml aml-triage-api && sleep 3 && curl -s localhost:8000/health && docker stop aml`

- [ ] T094 [US6] Record the demo
  - Milestone M9 / Type: docs / Depends: T092
  - Files: `deployment/demo/demo.gif` or `deployment/demo/demo.mp4` (health, valid score, invalid payload)
  - Accept: recording shows disclaimer in response; under 2 minutes
  - Verify: `ls -la deployment/demo/`

**Checkpoint**: US6 complete. Update README Optional Steps to "Step 8 attempted".

---

## Phase 9: User Story 7 — Optional Generative AI usage record and MLOps docs (Priority: P7, optional Step 9) — Milestone M9

**Goal**: Transparent record of any GenAI use, and the MLOps plan.

**Independent Test**: `docs/genai_usage.md` lists every use with the five required fields or
states "not used"; `docs/mlops_plan.md` covers env, config runs, tracking, CI, monitoring,
versioning/rollback.

- [ ] T095 [P] [US7] Write `docs/genai_usage.md`
  - Milestone M9 / Type: docs / Depends: T088
  - Files: `docs/genai_usage.md` (per use: tool and model, purpose, representative prompt and output, human review performed, limitations or corrections; include the Spec Kit-assisted specification and planning work in this repository; state that all factual text was verified against pipeline outputs)
  - Accept: no use lacks any of the five fields; or an explicit "not used" statement
  - Verify: `grep -c 'Human review' docs/genai_usage.md`

- [ ] T096 [P] [US7] Write `docs/mlops_plan.md`
  - Milestone M9 / Type: docs / Depends: T088
  - Files: `docs/mlops_plan.md` (reproducible environment, config-driven runs, recommended MLflow tracking, CI checks, monitoring plan: score-distribution drift, Recall@K on labeled batches, latency; versioning via `models/<version>` and rollback via `models/LATEST`)
  - Accept: each MLOps bullet from the assignment brief addressed
  - Verify: `grep -ciE 'monitor|rollback|version|tracking|CI' docs/mlops_plan.md`

- [ ] T097 [US7] Update README Optional Steps status
  - Milestone M9 / Type: docs / Depends: T094, T095, T096
  - Files: `README.md` (Steps 8 and 9 attempted/not attempted, with links)
  - Accept: status matches what exists in the repository
  - Verify: `grep -A6 'Optional Steps' README.md`

**Checkpoint**: Optional stories complete.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final gates, self-assessment, submission packaging.

- [ ] T098 Write the rubric self-assessment
  - Milestone M8 / Type: reports / Depends: T088 (and T097 if optional work done)
  - Files: `reports/rubric_self_assessment.md` (criteria 1–7 plus bonus against the "Outstanding/Exemplary" descriptors from `CAPSTONE_BRIEF.md`; evidence link per descriptor; gaps closed or acknowledged)
  - Accept: every descriptor has an evidence link or an acknowledged gap
  - Verify: `grep -c '](' reports/rubric_self_assessment.md`

- [ ] T099 Execute `specs/001-aml-risk-triage/quickstart.md` end to end
  - Milestone M6 / Type: verification / Depends: T098
  - Files: `specs/001-aml-risk-triage/quickstart.md` (fix any command that deviates from reality)
  - Accept: every expected outcome in the quickstart pass-criteria table observed
  - Verify: follow quickstart sections 1–9 (and 10 if Step 8 attempted)

- [ ] T100 Final vocabulary, disclaimer, secret, and history audit
  - Milestone M8 / Type: verification / Depends: T099
  - Files: none new
  - Accept: vocabulary test passes; every `reports/*.md`, deck, model card, and README carries the disclaimer; `detect-secrets` clean; `git log` contains no data or secret files in any commit; no force-pushes to `main`
  - Verify: `pytest -q && pre-commit run --all-files && git log --all --name-only --pretty=format: | sort -u | grep -E '\.(csv|parquet|joblib)$|^\.env$' ; test $? -eq 1`

- [ ] T101 Package submission files
  - Milestone M8 / Type: docs / Depends: T100
  - Files: `submission/` (gitignored or separate): `Your_Name_Pillar5_Capstone_Report.pdf`, `Your_Name_Pillar5_Capstone_Technical_Deck.pdf`, `Your_Name_Pillar5_Capstone_Business_Deck.pptx`, repository URL note, per `CAPSTONE_BRIEF.md` §8
  - Accept: approved formats only; names follow `Your_Name_Assignment name`
  - Verify: `ls submission/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1, M1)**: starts immediately; T015 is the gate.
- **Foundational (Phase 2, M2–M3)**: depends on T015; T017 can STOP the project on license; T025 requires the profiling narrative T022 (numbers before config).
- **US1 (Phase 3, M4–M6)**: depends on T034 and T036. Blocks US2–US5 because they consume the persisted model.
- **US2 (Phase 4)**: depends on T057 (bundle) and T060.
- **US3 (Phase 5)** and **US4 (Phase 6)**: both depend on T057; independent of each other except the shared notebook (T072 before T079).
- **US5 (Phase 7)**: depends on T059, T071, T078 (all narratives exist before the report is assembled).
- **US6 (Phase 8)** and **US7 (Phase 9)**: depend on T088 (core complete, gates G1–G11 evidenced).
- **Polish (Phase 10)**: depends on everything attempted.

### User Story Dependencies

- **US1** → requires Foundational only.
- **US2** → requires US1 bundle to reproduce-check; CI smoke (T063) can start after T057.
- **US3**, **US4** → require US1 bundle; can run in parallel with US2 and each other.
- **US5** → requires US1, US3, US4 narratives; US2 tolerance for §8.
- **US6**, **US7** → require US5 complete (constitutional ordering of optional work).

### Validate-before-concluding chain (enforced by ordering)

T021 → T022 → T025; T035 → T036; T038/T039 → T041; T049/T050; T056 → T057 → T059; T070 → T071;
T076 → T078; T080 → T082 → T083 → T084/T085.

### Parallel Opportunities

- Phase 1: T003, T004, T005, T007 together; T011, T012, T013 together.
- Phase 2: T019 alongside T020; T029, T030, T031 together after T028; T027 alongside T028.
- Phase 3: T038 and T039 together; T044, T045, T046, T047 together after T043; T051, T060 alongside narrative tasks.
- Phase 4–6: T063 alongside T061; T068, T069 alongside T067; T074, T075 alongside T073.
- Phase 7: T081 and T085 alongside T080/T083.
- Phase 8–9: T093 alongside T091; T095, T096 together.

---

## Parallel Example: User Story 1

```bash
# After T043 (model configs) completes, run these four together:
Task: "T044 Implement ranking comparators in src/aml_triage/models/comparators.py"
Task: "T045 Implement metric suite in src/aml_triage/evaluation/metrics.py"
Task: "T046 Implement capacity metrics in src/aml_triage/evaluation/capacity.py"
Task: "T047 Write tests/test_metrics.py and tests/test_capacity.py"

# After T034 completes, run these two together:
Task: "T038 Implement feature selection in src/aml_triage/features/selection.py"
Task: "T039 Implement PCA analysis in src/aml_triage/features/pca.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (M1) and commit.
2. Complete Phase 2 (M2–M3). Stop at T017 if the license blocks. Fill config only after reading profiling output (T022 → T025).
3. Complete Phase 3 (M4–M6). Touch the test split exactly once (T056).
4. **STOP and VALIDATE**: SC-001 and SC-002 assessed from `metrics.json`; queue output inspected.
5. Commit `model: select and persist <candidate> vX` with model card.

### Incremental Delivery

1. US2 makes the MVP auditable (clean-clone run, tolerance, CI).
2. US3 and US4 add explainability and the fairness analysis in parallel.
3. US5 assembles report and decks only from existing narratives.
4. US6 and US7 are attempted only if time remains after the core checkpoint at T088.

### Small-milestone discipline

- Commit after every task or tight group with conventional prefixes.
- Never write a narrative task before its numbers task is checked off.
- Never edit `configs/base.yaml` split or K values after T056 without a new config hash and a new model version.

---

## Notes

- [P] tasks touch different files and have no dependency on incomplete tasks.
- Every task lists its plan milestone so progress can also be tracked M1–M9.
- Notebooks never define logic; they call `aml_triage` and display artifacts.
- The test split is read by exactly one command run (T056). Everything downstream reads saved predictions.
- Optional work (Phases 8–9) is gated behind T088 by constitution Principle XI.
- All implementation commits land on `001-aml-risk-triage`. Merge to `main` only by pull request or squash merge after the T015, T060, T088, and T101 checkpoints (constitution Principle X).
