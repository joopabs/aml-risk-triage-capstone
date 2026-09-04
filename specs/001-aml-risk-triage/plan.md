# Implementation Plan: Explainable AML Transaction-Risk Triage

**Branch**: `001-aml-risk-triage` | **Date**: 2026-09-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-aml-risk-triage/spec.md`; constitution v1.0.0;
`PROJECT_DECISIONS.md`; `CAPSTONE_BRIEF.md`.

**Placeholder convention**: as in the spec, `[PROFILE]`, `[VERIFY]`, and `[MEASURED]` mark values
that this plan does not assert. Values recorded in `research.md` as "expected" come from the
public PaySim documentation and MUST be confirmed on first load (spec validation tasks V1–V13).

## Summary

Build a reproducible, leakage-safe, explainable binary classifier on PaySim that ranks synthetic
transactions for human investigator review at a fixed daily capacity K, evaluated primarily by
PR-AUC and Recall@K on a temporal held-out test set. The technical approach is a single Python
3.11 package (`src/aml_triage/`) exposing a config-driven CLI that runs nine milestones end to
end: scaffold and tests; acquisition, schema validation, and profiling; cleaning, EDA, and
causal feature engineering; feature selection and PCA; baseline plus three candidates on a
validation split; tuning, capacity analysis, one-shot test evaluation, and artifact persistence;
SHAP/PDP/ICE explainability with a Bias & Fairness Analysis built on an honest sensitive-attribute
availability check and a clearly labeled operational error-slice analysis; a final report and
two 8–12 slide decks; and, only after core gates pass, an optional FastAPI demo with MLOps and
GenAI documentation. Every fitted transform lives inside a scikit-learn `Pipeline` fitted on
training rows only, and a leakage test suite guards the split.

## Technical Context

**Language/Version**: Python 3.11.12 (pyenv-managed locally; declared in `.python-version` and
`pyproject.toml` `requires-python = ">=3.11,<3.12"`).

**Primary Dependencies**: pandas, numpy, scikit-learn, imbalanced-learn, shap, matplotlib,
seaborn, joblib, pyarrow (parquet I/O for processed splits), pyyaml (configs), pydantic
(config and schema validation). Dev: pytest, pytest-cov, ruff, detect-secrets, pre-commit,
nbconvert, jupyter. Optional (Step 8 only): fastapi, uvicorn, httpx (API tests). Gradient
boosting uses scikit-learn `HistGradientBoostingClassifier`; XGBoost is a documented alternative
(see `research.md` R-03). Exact versions pinned in `requirements.txt` generated from
`requirements.in` with `uv pip compile`.

**Storage**: Local filesystem only. Raw CSV under `data/raw/` (gitignored), processed parquet
splits under `data/processed/` (gitignored), artifacts under `models/<model_version>/` and
`reports/`. No database.

**Testing**: pytest with unit tests (features, metrics, schema), leakage-guard tests, config
tests, a vocabulary/disclaimer scan test, and optional API contract tests via `httpx`.
Coverage threshold on `src/aml_triage`: 80% lines (see `pyproject.toml`).

**Target Platform**: macOS/Linux developer machine; verified locally on macOS (Darwin 23.6,
8 cores, 16 GB RAM) and in a GitHub Actions `ubuntu-latest` CI job on a seeded subsample.

**Project Type**: Single Python package + CLI (data science pipeline), with an optional
web-service module.

**Performance Goals**: Full pipeline (fetch excluded) completes on the local machine in under
60 minutes wall clock with the default config; hyperparameter search runs on a seeded training
subsample so it completes in under 20 minutes; CI smoke run on a small seeded sample completes
in under 10 minutes. Optional API returns a score in under 500 ms per request locally.

**Constraints**: Peak memory under 12 GB (dtype downcasting on load, parquet intermediates).
Deterministic outputs given `seed` and single-threaded or fixed-thread settings where a library
is otherwise non-deterministic; any residual tolerance documented (spec V13). No data or secrets
in Git. Every output surface carries the disclaimer constant.

**Scale/Scope**: One dataset, expected on the order of millions of rows and eleven columns
`[VERIFY on load]`; one target; four models plus three ranking comparators; one selected model;
one report; two decks; roughly 26 source modules, 8 notebooks, and 13 test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (see end of section).*

| Gate | Constitution requirement | Plan element satisfying it | Status |
|------|--------------------------|----------------------------|--------|
| G1 Framing | Problem, task, unit, PR-AUC primary, Recall@K with stated K, illustrative KPI | Spec "Business Context"; `configs/base.yaml` holds `review_capacity_k` and `k_grid`; `src/aml_triage/evaluation/capacity.py` computes Recall@K/Precision@K per review period; report §1 | PASS |
| G2 Provenance | Source, date, checksum, license recorded; synthetic labeling; raw data gitignored; secret scan | M2 `scripts/fetch_data.sh` + `data/README.md` + `configs/data_source.yaml` (URL, sha256, license text, date); `.gitignore`; `detect-secrets` pre-commit + CI | PASS |
| G3 Reproducibility | Pinned deps, global seed, versioned artifacts, README commands verified clean | `requirements.in` → pinned `requirements.txt`; `seed` in config propagated via `aml_triage.utils.seed`; `models/<version>/`; `Makefile` targets; CI runs `make ci` on fresh runner | PASS |
| G4 Leakage | Temporal split documented; train-only fitting; causal aggregates; leakage test | `split.py` temporal by `step`; all transforms in `sklearn.Pipeline`; `features/aggregates.py` uses shifted cumulative stats; `tests/test_leakage.py` | PASS |
| G5 Data quality | Nulls, dups, outliers, invalid values, imbalance, limitations; data dictionary | M2 `profiling.py` → `reports/data_quality.md` + JSON; `reports/data_dictionary.md` generated from `configs/schema.yaml` + engineered feature registry | PASS |
| G6 EDA & FE | EDA visuals; per-feature rationale; ≥1 selection; PCA with stated role | M3 notebooks 02–03 + `src/aml_triage/eda/`; feature registry with `rationale` and `available_at_prediction_time` fields; M4 `selection.py` (mutual information filter + L1 embedded) and `pca.py` | PASS |
| G7 Models | Dummy + ≥3 candidates; same split/metrics/K; selection matrix | M5–M6 `models/registry.py` (dummy, LR, balanced RF, HGB) + comparators (random, rule); `evaluation/compare.py` → `reports/model_comparison.md`, selection matrix | PASS |
| G8 Explainability | SHAP global + local; PDP/ICE or documented alternative; plain language | M7 `explain/shap_reports.py`, `explain/pdp_ice.py`; captions from `explain/captions.py`; figures in `reports/figures/explain/` | PASS |
| G9 Ethics & fairness | Availability check; demographic metrics OR limitation + operational slices labeled as such; audit plan; mitigations; limitations | M7 `fairness/availability.py` (schema-driven), `fairness/slices.py` (labels output "operational error-slice analysis"), report §6 template with mandatory subsections | PASS |
| G10 Human-in-the-loop | Disclaimer everywhere; prohibited actions absent; vocabulary audited | `aml_triage/constants.py::DISCLAIMER`; every writer appends it; `tests/test_vocabulary.py` scans `src/`, `reports/`, `notebooks/` for prohibited terms with allowlist | PASS |
| G11 Communication | Two 8–12 slide decks; report; README | M8 `notebooks/90_technical_deck.ipynb` → nbconvert slides; business deck outline `reports/slides/business_deck_outline.md` → PPTX/PDF; `reports/final_report.md` → PDF; slide-count check script | PASS |
| G12 Optional transparency | Status of Steps 8/9 stated; deliverables if attempted | README "Optional steps" section; M9 `src/aml_triage/api/`, `deployment/`, `docs/genai_usage.md` | PASS |

**Principle spot-checks**

- P I: accuracy is computed but never in headline tables; `compare.py` places it last with prevalence.
- P II: PaySim described as synthetic mobile-money data in `data/README.md`, README, report, decks.
- P VI: deep learning not planned; justification recorded in `research.md` R-03.
- P IX: API response schema has no allow/block field (see `contracts/scoring-api.yaml`).
- P XI: optional module import-isolated; `tests/test_core_without_optional.py` asserts core runs
  with `aml_triage.api` absent.

**Pre-Phase-0 result**: no violations. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-aml-risk-triage/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli-contract.md          # CLI commands, inputs, outputs, exit codes
│   ├── artifacts-contract.md    # On-disk artifact and metrics schemas
│   ├── config-schema.md         # configs/*.yaml keys and validation rules
│   └── scoring-api.yaml         # OpenAPI 3.1 for optional Step 8 service
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
.
├── README.md
├── LICENSE                          # MIT (code only; data governed by source license)
├── requirements.in                  # top-level deps
├── requirements.txt                 # pinned via uv pip compile
├── requirements-dev.in / -dev.txt   # dev/test tooling
├── requirements-api.in / -api.txt   # optional Step 8 only
├── pyproject.toml                   # package metadata, ruff, pytest, coverage config
├── .python-version                  # 3.11.12
├── Makefile                         # setup, data, pipeline, test, report, ci targets
├── .gitignore                       # data/raw, data/processed, models/*/*.joblib, .env, etc.
├── .pre-commit-config.yaml          # ruff, ruff-format, detect-secrets, nbstripout
├── .secrets.baseline                # detect-secrets baseline
├── .env.example                     # KAGGLE_USERNAME/KAGGLE_KEY placeholders (optional path)
├── .github/workflows/ci.yml         # lint + tests + smoke pipeline on seeded sample
├── configs/
│   ├── base.yaml                    # seed, paths, K, k_grid, review_period_steps, split bounds
│   ├── data_source.yaml             # URL, filename, sha256, license text/date, download date
│   ├── schema.yaml                  # expected columns, dtypes, constraints (V2)
│   ├── features.yaml                # feature registry: name, formula ref, rationale, pred-time flag, set membership
│   ├── models/
│   │   ├── dummy.yaml
│   │   ├── logreg.yaml
│   │   ├── balanced_rf.yaml
│   │   └── hgb.yaml
│   ├── vocabulary.yaml              # prohibited terms + allowlist for the vocabulary test
│   └── smoke.yaml                   # overrides for CI sample run
├── data/
│   ├── README.md                    # provenance, license, checksum, fetch command, synthetic notice
│   ├── raw/                         # gitignored
│   └── processed/                   # gitignored (parquet splits, feature matrices)
├── scripts/
│   ├── fetch_data.sh                # kaggle API if creds present, else manual-download instructions; verifies sha256
│   ├── make_sample.py               # seeded stratified sample for CI smoke
│   ├── export_report.sh             # markdown → PDF (pandoc if available)
│   └── check_slide_counts.py        # asserts 8–12 slides per deck
├── src/aml_triage/
│   ├── __init__.py
│   ├── constants.py                 # DISCLAIMER, MODEL_OUTPUT_FIELDS, PROHIBITED_TERMS ref
│   ├── config.py                    # pydantic models loading configs/*.yaml
│   ├── cli.py                       # `python -m aml_triage <command>` (see contracts/cli-contract.md)
│   ├── __main__.py                  # entry point delegating to cli.main
│   ├── utils/
│   │   ├── seed.py                  # set_global_seed(seed) → numpy, random, PYTHONHASHSEED note
│   │   ├── io.py                    # parquet/json/joblib helpers, model_version()
│   │   └── logging.py
│   ├── data/
│   │   ├── load.py                  # read raw CSV with dtype map
│   │   ├── schema.py                # validate against configs/schema.yaml (FR-020)
│   │   ├── profiling.py             # data quality report (FR-021)
│   │   ├── dictionary.py            # data dictionary generator (FR-023)
│   │   └── split.py                 # temporal split by step; fallback stratified (FR-040/041)
│   ├── eda/
│   │   └── plots.py                 # EDA figures (M3)
│   ├── features/
│   │   ├── base.py                  # feature registry loader, prediction-time flags
│   │   ├── transaction.py           # type encoding, log amount, ratios, buckets, deltas, flags
│   │   ├── aggregates.py            # causal prior-transaction aggregates (FR-032)
│   │   ├── selection.py             # MI filter + L1 embedded (FR-034)
│   │   ├── pca.py                   # PCA fit/report (FR-035)
│   │   └── pipeline.py              # build sklearn ColumnTransformer/Pipeline per feature set
│   ├── models/
│   │   ├── registry.py              # candidate factory from configs/models/*.yaml
│   │   ├── comparators.py           # random ranking, rule baseline
│   │   ├── train.py                 # fit on train, predict on val/test
│   │   └── tune.py                  # RandomizedSearchCV on seeded train subsample, val scoring
│   ├── evaluation/
│   │   ├── metrics.py               # PR-AUC, ROC-AUC, P/R/F1, FPR, Brier, ECE, confusion
│   │   ├── capacity.py              # Recall@K / Precision@K per review period, tie-break
│   │   ├── calibration.py           # curves, optional isotonic on validation
│   │   ├── bootstrap.py             # CI for PR-AUC and Recall@K
│   │   ├── compare.py               # comparison tables + selection matrix
│   │   └── threshold.py             # operating point chosen on validation
│   ├── explain/
│   │   ├── shap_reports.py          # global + local SHAP
│   │   ├── pdp_ice.py               # PDP/ICE with validity checks
│   │   └── captions.py              # plain-language captions + disclaimer
│   ├── fairness/
│   │   ├── availability.py          # sensitive-attribute availability record (FR-070)
│   │   ├── slices.py                # operational error-slice analysis (FR-073)
│   │   ├── demographic.py           # DP/EO/DI, executed only if availability says valid labels
│   │   └── report.py                # writes bias_fairness_analysis.md with the six required headings
│   ├── reporting/
│   │   ├── figures.py               # consistent matplotlib/seaborn styling, save helpers
│   │   ├── tables.py                # markdown table writers with disclaimer footer
│   │   └── report_builder.py        # assembles reports/final_report.md from sections
│   └── api/                         # OPTIONAL Step 8; not imported by core
│       ├── main.py                  # FastAPI app
│       ├── schemas.py               # pydantic request/response (no allow/block field)
│       └── service.py               # loads models/<version>/pipeline.joblib
├── notebooks/
│   ├── 01_data_acquisition_and_schema.ipynb
│   ├── 02_data_quality_and_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_feature_selection_and_pca.ipynb
│   ├── 05_model_comparison_validation.ipynb
│   ├── 06_tuning_capacity_and_test.ipynb
│   ├── 07_explainability_and_fairness.ipynb
│   └── 90_technical_deck.ipynb      # nbconvert --to slides
├── models/
│   └── <model_version>/             # pipeline.joblib, model_card.md, config_snapshot.yaml, metrics.json (pipeline.joblib always gitignored, pipeline.sha256 committed; regenerate via `make pipeline`; model_card + metrics committed)
├── reports/
│   ├── final_report.md / .pdf
│   ├── sections/                    # hand-authored 01_problem.md, 07_limitations.md, 08_reproducibility.md
│   ├── data_quality.md, data_quality.json
│   ├── data_dictionary.md
│   ├── eda_summary.md
│   ├── feature_selection.md, pca_report.md
│   ├── model_comparison.md, selection_matrix.md
│   ├── capacity_analysis.md
│   ├── explainability.md
│   ├── bias_fairness_analysis.md
│   ├── rubric_self_assessment.md
│   ├── figures/{eda,features,models,explain,fairness}/
│   └── slides/
│       ├── technical_deck.html / .pdf
│       ├── business_deck_outline.md
│       └── business_deck.pptx / .pdf
├── tests/
│   ├── conftest.py                  # tiny synthetic fixture frame (not PaySim rows)
│   ├── test_config.py
│   ├── test_schema.py
│   ├── test_split.py
│   ├── test_leakage.py              # FR-043
│   ├── test_features.py
│   ├── test_aggregates_causal.py
│   ├── test_metrics.py
│   ├── test_capacity.py             # ties, short periods
│   ├── test_vocabulary.py           # FR-084
│   ├── test_no_hardcoded_params.py  # FR-101: notebooks/scripts read seed, K, split, threshold from config
│   ├── test_fairness.py             # DP/EO/DI on fixture with synthetic group column
│   ├── test_core_without_optional.py
│   └── api/test_scoring_api.py      # optional, skipped if fastapi missing
├── deployment/                      # OPTIONAL Step 8
│   ├── Dockerfile
│   ├── DEPLOYMENT.md
│   └── demo/                        # GIF/screencast
└── docs/
    ├── genai_usage.md               # OPTIONAL Step 9 (or "not used" statement)
    └── mlops_plan.md                # monitoring, versioning, rollback (optional)
```

**Structure Decision**: Single Python package under `src/aml_triage` with a thin CLI, because
the deliverable is a reproducible pipeline rather than an application. Notebooks import from
the package and read config; they never define logic. The optional API is a subpackage that the
core never imports, satisfying P XI. This matches the constitution's required top-level layout
(`src/`, `notebooks/`, `data/`, `models/`, `reports/`, `tests/`, `configs/`) with additive
`scripts/`, `deployment/`, and `docs/` directories.

## Milestones

Each milestone lists files, dependencies, verification commands, expected artifacts, and
leakage/privacy controls. Milestones map to `/speckit-tasks` phases. "Verify" commands are
the acceptance checks a reviewer runs; they are also `make` targets.

### M1: Repository scaffold, configuration, quality tooling, and tests

**Goal**: A clean clone installs, lints, and passes a starter test suite; configs and the
disclaimer constant exist before any data is touched. Gates: G3, G10 (partial), G2 (secret scan).

**Files**: `pyproject.toml`, `.python-version`, `requirements*.in/.txt`, `Makefile`,
`.gitignore`, `.pre-commit-config.yaml`, `.secrets.baseline`, `.env.example`,
`.github/workflows/ci.yml`, `LICENSE`, `README.md` (skeleton with disclaimer and synthetic-data
notice), `configs/base.yaml`, `configs/vocabulary.yaml`, `configs/smoke.yaml`,
`src/aml_triage/{__init__,constants,config,cli}.py`, `src/aml_triage/utils/*`,
`tests/{conftest,test_config,test_vocabulary,test_core_without_optional}.py`, `data/README.md`
(placeholder sections), empty `notebooks/`, `models/`, `reports/figures/` with `.gitkeep`.

**Dependencies**: Python 3.11.12 (pyenv), `uv`. No data.

**Verification**:

```bash
make setup            # python -m venv .venv && uv pip sync requirements.txt requirements-dev.txt
make lint             # ruff check . && ruff format --check .
make test             # pytest -q  (starter tests: config loads, seed helper, disclaimer present, vocabulary clean)
pre-commit run --all-files
git status --porcelain  # must not list data/ or .env
```

**Expected artifacts**: green `make lint test`; `.secrets.baseline`; CI workflow passing on
push; `configs/base.yaml` with `seed`, `paths`, `review_capacity_k: null  # set after V8`,
`k_grid`, `review_period_steps: null  # set after profiling`, `split: {strategy: temporal, train_end_step: null, val_end_step: null}`.

**Leakage/privacy controls**: `.gitignore` covers `data/raw/`, `data/processed/`, `*.csv`,
`*.parquet`, `.env`, `models/**/*.joblib`; `detect-secrets` blocks secrets pre-commit and in CI;
`.env.example` contains placeholders only.

### M2: Dataset acquisition, data dictionary, schema validation, and profiling

**Goal**: Data is fetched reproducibly, its provenance and license recorded, its schema enforced,
and its quality profiled, resolving spec validation tasks V1–V6 and V8. Gates: G2, G5.

**Files**: `scripts/fetch_data.sh`, `configs/data_source.yaml`, `configs/schema.yaml`,
`src/aml_triage/data/{load,schema,profiling,dictionary}.py`,
`notebooks/01_data_acquisition_and_schema.ipynb`, `tests/test_schema.py`, `data/README.md`
(completed), `reports/data_quality.md`, `reports/data_quality.json`, `reports/data_dictionary.md`.

**Dependencies**: M1; network access once; optional Kaggle API credentials via environment
(never committed); otherwise a manual download step documented in `data/README.md`.

**Verification**:

```bash
make data             # scripts/fetch_data.sh → data/raw/<file>.csv; verifies sha256 against configs/data_source.yaml
python -m aml_triage validate-schema --config configs/base.yaml     # exit 0; exit 2 on schema mismatch
python -m aml_triage profile --config configs/base.yaml             # writes reports/data_quality.*
python -m aml_triage data-dictionary --config configs/base.yaml     # writes reports/data_dictionary.md
pytest tests/test_schema.py -q
grep -q "synthetic" data/README.md && grep -q "License" data/README.md
```

**Expected artifacts**: `data/raw/<file>.csv` (local only); `configs/data_source.yaml` with
`url`, `filename`, `sha256`, `downloaded_on`, `license_text_verbatim`, `license_verified_on`;
`reports/data_quality.md` containing row count, null counts, exact/near-duplicate counts,
outlier summary (IQR and per-type quantiles), invalid-value counts (negative/zero amounts,
negative balances, balance-arithmetic inconsistency per type), class ratio overall and by
`type` and by `step`, transactions per step, sensitive-attribute availability pre-check
(column-name scan), and source-data limitations; `reports/data_dictionary.md` for raw columns
(engineered columns appended in M3).

**Leakage/privacy controls**: profiling runs on the full raw file for descriptive purposes
only; no modeling decision is fitted here. Profiling output contains aggregates only, no row
dumps (FR-015). Checksum verification prevents silent dataset substitution. Fetch script
refuses to run if `data/raw/` is tracked by git.

### M3: Cleaning, EDA, leakage-safe feature engineering, and visual reports

**Goal**: A temporal split with recorded boundaries; cleaning decisions tied to profiling
findings; engineered features with rationale and prediction-time flags; EDA figures regenerated
by code. Resolves V9, V10, V5. Gates: G4, G6.

**Files**: `src/aml_triage/data/split.py`, `src/aml_triage/features/{base,transaction,aggregates,pipeline}.py`,
`src/aml_triage/eda/*` (plots), `configs/features.yaml`, `configs/base.yaml` (split bounds and
`review_period_steps` filled), `notebooks/02_data_quality_and_eda.ipynb`,
`notebooks/03_feature_engineering.ipynb`, `tests/{test_split,test_leakage,test_features,test_aggregates_causal}.py`,
`reports/eda_summary.md`, `reports/figures/eda/*`, `reports/data_dictionary.md` (engineered rows added).

**Dependencies**: M2 outputs (profiling determines split bounds and whether positives exist in
later steps; determines which candidate features are computable).

**Verification**:

```bash
python -m aml_triage split --config configs/base.yaml        # writes data/processed/{train,val,test}.parquet + split_manifest.json
python -m aml_triage build-features --config configs/base.yaml --feature-set primary
python -m aml_triage eda --config configs/base.yaml           # writes reports/eda_summary.md + figures
pytest tests/test_split.py tests/test_leakage.py tests/test_features.py tests/test_aggregates_causal.py -q
```

**Expected artifacts**: `data/processed/split_manifest.json` (row counts, step ranges, positive
counts per split, strategy, config hash); feature matrices per split; `configs/features.yaml`
with, per feature: `name`, `source_columns`, `transform`, `rationale`, `available_at_prediction_time`,
`sets: [primary, posttx_ablation]`; EDA figures (univariate, class-conditional, correlation
heatmap, positives over step, per-type amount distributions); `reports/eda_summary.md`.

**Leakage/privacy controls**: split is temporal by `step` with `train_end_step < val_end_step`;
`test_leakage.py` asserts disjoint indices, monotone step ranges, and that `Pipeline.fit` was
called only with training rows (via a fit-recording wrapper); aggregates use group-wise
cumulative statistics shifted by one within step order so a row never sees itself or later rows
(`test_aggregates_causal.py` checks against a brute-force implementation on the fixture);
account identifiers are dropped after aggregation (FR-033); post-transaction balance-derived
features are tagged `available_at_prediction_time: batch_only` and confined to the
`posttx_ablation` set (see `research.md` R-06); cleaning thresholds computed on training rows
only and stored in the pipeline.

### M4: Feature selection and PCA analysis

**Goal**: At least one selection method and PCA, both fitted on training data only, with
before/after evidence and a stated PCA role. Gate: G6.

**Files**: `src/aml_triage/features/{selection,pca}.py`, `notebooks/04_feature_selection_and_pca.ipynb`,
`reports/feature_selection.md`, `reports/pca_report.md`, `reports/figures/features/*`,
`configs/features.yaml` (adds `selected` set), `tests/test_features.py` (selection fit-scope test).

**Dependencies**: M3 feature matrices.

**Verification**:

```bash
python -m aml_triage select-features --config configs/base.yaml   # MI filter + L1 embedded; writes report + updates selected set
python -m aml_triage pca --config configs/base.yaml               # scree, cumulative variance, 2-D projection colored by label
pytest tests/test_features.py -q -k "selection or pca"
```

**Expected artifacts**: `reports/feature_selection.md` with before/after feature lists and
scores for both methods; `reports/pca_report.md` stating role (diagnostic and visualization;
optional `pca_variant` feature set for one candidate) with explained-variance table;
figures (scree, 2-D projection).

**Leakage/privacy controls**: `SelectKBest`/L1 selector and `PCA` are pipeline steps fitted on
training rows only; validation and test are transformed only; the fit-scope test asserts this.

### M5: Baseline and multi-model validation comparison

**Goal**: Dummy baseline, random and rule comparators, and three candidates trained on train and
compared on validation with the full metric suite and Recall@K/Precision@K at the config K grid.
Gate: G7 (validation half).

**Files**: `src/aml_triage/models/{registry,comparators,train}.py`,
`src/aml_triage/evaluation/{metrics,capacity,calibration,compare}.py`, `configs/models/*.yaml`,
`notebooks/05_model_comparison_validation.ipynb`, `tests/{test_metrics,test_capacity}.py`,
`reports/model_comparison.md` (validation section), `reports/figures/models/*`.

**Dependencies**: M3–M4 pipelines and feature sets.

**Verification**:

```bash
python -m aml_triage train --config configs/base.yaml --models dummy,logreg,balanced_rf,hgb --split val
python -m aml_triage compare --config configs/base.yaml --split val   # writes validation comparison tables + PR/ROC/calibration curves
pytest tests/test_metrics.py tests/test_capacity.py -q
```

**Expected artifacts**: per-model validation `metrics.json`; `reports/model_comparison.md`
validation tables (PR-AUC, ROC-AUC, P/R/F1 at default 0.5 and at operating point, FPR, Brier,
ECE, Recall@K and Precision@K for each K in grid, per-period mean and pooled); PR, ROC,
calibration curves; class prevalence line next to any accuracy.

**Leakage/privacy controls**: no test predictions are produced in M5 (CLI refuses `--split test` before M6
`freeze` step); imbalance handling via `class_weight` or `imblearn.Pipeline` sampler so
resampling occurs inside fit only; `test_capacity.py` covers ties (deterministic tie-break:
score desc, step asc, row index asc) and periods with fewer than K rows.

### M6: Tuning, threshold/review-capacity analysis, final test evaluation, and artifact persistence

**Goal**: Tune each candidate on a seeded training subsample scored on validation; choose the
operating point on validation; evaluate all models once on test with bootstrap CIs; build the
selection matrix; persist the selected model with version, config snapshot, and model card.
Resolves V11, V13. Gate: G7 (complete), G3.

**Files**: `src/aml_triage/models/tune.py`, `src/aml_triage/evaluation/{threshold,bootstrap,compare}.py`,
`src/aml_triage/utils/io.py` (`model_version()`), `notebooks/06_tuning_capacity_and_test.ipynb`,
`reports/model_comparison.md` (test section), `reports/selection_matrix.md`,
`reports/capacity_analysis.md`, `models/<model_version>/{pipeline.joblib,config_snapshot.yaml,metrics.json,model_card.md}`,
`models/LATEST` (text file with version id).

**Dependencies**: M5. Compute budget per Technical Context.

**Verification**:

```bash
python -m aml_triage tune --config configs/base.yaml --models logreg,balanced_rf,hgb   # RandomizedSearchCV on seeded subsample; scores on val
python -m aml_triage choose-operating-point --config configs/base.yaml                # threshold/top-K on validation; writes configs/operating_point.yaml
python -m aml_triage freeze --config configs/base.yaml                                # marks test as unlockable exactly once; records hash
python -m aml_triage evaluate --config configs/base.yaml --split test                 # all models, one pass, bootstrap CIs
python -m aml_triage select --config configs/base.yaml                                # selection matrix + persists models/<version>/
python -m aml_triage reproduce-check --config configs/base.yaml                       # re-runs selected model fit twice, diffs metrics, records tolerance
pytest -q
```

**Expected artifacts**: tuned params per model in `configs/models/*.tuned.yaml`;
`configs/operating_point.yaml`; `reports/capacity_analysis.md` (Recall@K and Precision@K vs K
curve, per-period distribution, FP/FN trade-off narrative); test metrics with 95% bootstrap CIs
for PR-AUC and Recall@K; `reports/selection_matrix.md` (PR-AUC, Recall@K, Precision@K,
calibration, explainability, inference/maintenance risk, investigator workload, verdict);
`models/<version>/` bundle; `model_card.md` includes intended use, non-use, disclaimer, data
provenance, metrics, limitations.

**Leakage/privacy controls**: tuning reads train and val only; `freeze` writes
`data/processed/test_access.json` and `evaluate --split test` refuses to run twice for the same
config hash without `--force-reevaluate --reason "..."` (reason logged to the report); operating
point fixed before test is read; bootstrap resamples test rows only for CIs, never for
selection; model card contains no row-level data.

### M7: Explainability, ethical AI, fairness limitations, operational-slice analysis, and governance recommendations

**Goal**: SHAP global and local explanations, PDP/ICE with validity checks, the
sensitive-attribute availability record, either demographic fairness metrics or an explicit
"cannot be measured" statement plus a correctly labeled operational error-slice analysis,
limitations, mitigations, and a governance audit plan. Resolves V7, V12. Gates: G8, G9, G10.

**Files**: `src/aml_triage/explain/{shap_reports,pdp_ice,captions}.py`,
`src/aml_triage/fairness/{availability,slices,demographic}.py`,
`notebooks/07_explainability_and_fairness.ipynb`, `reports/explainability.md`,
`reports/bias_fairness_analysis.md`, `reports/figures/{explain,fairness}/*`,
`tests/test_vocabulary.py` (extended with fairness-labeling assertions).

**Dependencies**: M6 selected model bundle; test split predictions saved in M6.

**Verification**:

```bash
python -m aml_triage explain --config configs/base.yaml --model LATEST        # SHAP global (seeded sample), ≥3 local top-K waterfalls, PDP/ICE with validity report
python -m aml_triage fairness-availability --config configs/base.yaml         # writes availability record
python -m aml_triage fairness --config configs/base.yaml                      # demographic metrics if valid labels, else operational error-slice analysis
pytest tests/test_vocabulary.py -q                                            # asserts "operational error-slice analysis" label and absence of "demographic fairness" claims when availability=false
```

**Expected artifacts**: SHAP summary and bar plots; ≥3 local waterfall plots with plain-language
captions and disclaimer; PDP/ICE figures for top features or a documented alternative
(permutation importance) with reasons; `reports/explainability.md` with consistency discussion
against EDA; `reports/bias_fairness_analysis.md` with mandatory subsections: Sensitive-Attribute
Availability Record, Demographic Fairness (metrics or explicit non-measurability statement),
Operational Error-Slice Analysis (by `type`, amount band, origin-balance band, step band;
error rates, Recall@K, calibration per slice), Limitations, Mitigations, Governance-Controlled
Fairness Audit Plan (data, metrics, owners, cadence).

**Leakage/privacy controls**: explanations computed on test predictions from the frozen model
only; SHAP background sampled from training rows (seeded); slices use non-protected operational
fields only; `test_vocabulary.py` fails the build if operational slices are described with
protected-group fairness terms; no account identifiers or row dumps appear in figures or
captions.

### M8: Final report and two 8–12 slide presentation decks

**Goal**: Assemble the final report from generated sections; produce the technical deck via
nbconvert slides and the business deck from a committed outline; export approved formats;
complete the rubric self-assessment. Gate: G11.

**Files**: `src/aml_triage/reporting/report_builder.py`, `reports/final_report.md` (+ `.pdf`),
`notebooks/90_technical_deck.ipynb` → `reports/slides/technical_deck.{html,pdf}`,
`reports/slides/business_deck_outline.md`, `reports/slides/business_deck.{pptx,pdf}`,
`reports/rubric_self_assessment.md`, `scripts/{export_report.sh,check_slide_counts.py}`,
`README.md` (completed: purpose, disclaimer, provenance, commands, repo map, results summary,
links, optional-step status).

**Dependencies**: M2–M7 reports and figures; pandoc or a documented alternative for PDF export
(`research.md` R-11); PowerPoint/Canva/Google Slides for the business deck.

**Verification**:

```bash
python -m aml_triage build-report --config configs/base.yaml     # assembles reports/final_report.md from section files
scripts/export_report.sh                                          # → reports/final_report.pdf
jupyter nbconvert notebooks/90_technical_deck.ipynb --to slides --output-dir reports/slides --output technical_deck
python scripts/check_slide_counts.py reports/slides/technical_deck.html reports/slides/business_deck.pptx   # 8 ≤ n ≤ 12 each
pytest tests/test_vocabulary.py -q                                # scans final report and deck outlines
grep -c "illustrative" reports/slides/business_deck_outline.md    # ≥ number of KPI figures shown
```

**Expected artifacts**: `reports/final_report.md/.pdf` with sections §1 Problem, §2 Data and
Dictionary, §3 EDA + Feature Engineering, §4 Models and Selection, §5 Explainability, §6 Bias &
Fairness Analysis, §7 Limitations, §8 Reproducibility; technical deck (8–12 slides: framing,
data, quality, features, split, comparison, selection, explainability, fairness, reproducibility,
next steps); business deck (8–12 slides: problem, what the tool does and does not do, how
investigators use it, illustrative KPI, risks, governance and human-in-the-loop, what real
deployment would require, ask/next steps); `reports/rubric_self_assessment.md` against the
"Outstanding/Exemplary" descriptors for criteria 1–7 plus bonus.

**Leakage/privacy controls**: report and decks contain aggregates and clearly labeled synthetic
illustrative examples only; every numeric business claim is prefixed "illustrative"; disclaimer
on title and closing slides and in report front matter; vocabulary test scans all prose.

### M9: Optional FastAPI demo and MLOps/GenAI documentation

**Goal**: Only after G1–G11 pass: a local scoring service reusing the persisted pipeline, a
deployment guide and demo recording, an MLOps plan, containerization, and a GenAI usage record
(or an explicit "not used" statement). Gate: G12.

**Files**: `src/aml_triage/api/{main,schemas,service}.py`, `requirements-api.in/.txt`,
`tests/api/test_scoring_api.py`, `deployment/{Dockerfile,DEPLOYMENT.md,demo/*}`,
`docs/{mlops_plan.md,genai_usage.md}`, `README.md` (optional-step status updated),
`.github/workflows/ci.yml` (API tests job, conditional).

**Dependencies**: M6 `models/LATEST`; fastapi, uvicorn, httpx; Docker (present locally).

**Verification**:

```bash
uv pip sync requirements.txt requirements-api.txt
uvicorn aml_triage.api.main:app --port 8000 &
curl -s localhost:8000/health
curl -s -X POST localhost:8000/score -H 'content-type: application/json' -d @contracts/examples/score_request.json   # response has score, review_priority, model_version, disclaimer; no allow/block field
pytest tests/api -q
docker build -t aml-triage-api deployment/ && docker run --rm -p 8000:8000 aml-triage-api   # then repeat health/score checks
pytest tests/test_core_without_optional.py -q   # core unaffected by API absence
```

**Expected artifacts**: running local service conforming to `contracts/scoring-api.yaml`;
`deployment/DEPLOYMENT.md` (run, container, config, model version, rollback steps);
`deployment/demo/demo.gif` or screencast; `docs/mlops_plan.md` (reproducible env, config-driven
runs, optional MLflow tracking note, CI checks, monitoring plan: score distribution drift,
Recall@K on labeled batches, latency; versioning and rollback via `models/<version>` and
`models/LATEST`); `docs/genai_usage.md` per FR-112.

**Leakage/privacy controls**: service loads only the frozen artifact; request schema accepts
transaction fields only (no identifiers required beyond what aggregates need, and none are
logged); response excludes any decision field; disclaimer in every response and in `/health`;
no request bodies persisted; container image excludes `data/`; API dependencies isolated in
`requirements-api.txt`.

## Complexity Tracking

No constitution violations identified; table intentionally empty.

## Phase 0 and Phase 1 outputs

- `research.md`: decisions R-01 to R-14 resolving environment, boosting library, acquisition
  path, scale handling, split design, post-transaction feature policy, aggregates, selection
  and PCA method choice, calibration, capacity metric definition, report/deck tooling, secret
  scanning, reproducibility tolerance, and optional-work boundaries.
- `data-model.md`: entities, fields, validation rules, and state transitions for the split,
  feature registry, model bundle, evaluation run, review queue, and fairness records.
- `contracts/`: CLI contract, artifact and metrics schemas, config schema, and the optional
  scoring API OpenAPI document.
- `quickstart.md`: clean-clone validation walkthrough for a reviewer.

## Constitution Check (post-design re-evaluation)

Re-evaluated after writing `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`:

- G4: the `freeze`/`evaluate` contract and fit-scope wrapper in `contracts/cli-contract.md`
  make train-only fitting and single-touch test enforceable, not merely documented. PASS.
- G9: `data-model.md` defines `SensitiveAttributeAvailabilityRecord` and requires the fairness
  report to branch on it; `OperationalSliceResult.label` is a fixed literal. PASS.
- G10: `contracts/scoring-api.yaml` response schema has `additionalProperties: false` and no
  decision field; disclaimer is a required string. PASS.
- G12: optional API is a separate requirements file and subpackage; `quickstart.md` shows the
  core path succeeding without it. PASS.
- No new violations introduced. Complexity Tracking remains empty.
