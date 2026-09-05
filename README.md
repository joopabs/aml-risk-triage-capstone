# Explainable AML Transaction-Risk Triage for SME and Corporate Banking

An end-to-end, reproducible, responsible machine-learning capstone (Pillar 5). The model ranks
**synthetic** PaySim transactions so a fixed daily investigator capacity is spent on the
transactions most worth a human look. It is a decision-support prototype, not a decision system.

> **Disclaimer.** Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.

> **Synthetic data notice.** PaySim is synthetic mobile-money transaction data. It is not real
> SME, corporate, or Philippine banking data. Every figure in this repository is therefore about
> simulated fraud in synthetic data and is labeled "illustrative" where it describes business
> value.

**What this system does not do:** no automatic blocking, account closure, customer risk rating,
regulatory reporting, or AML determination. A human investigator reviews, decides, and can
override.

## Status

Milestones 1–6 are complete: scaffold and tooling, PaySim acquired with recorded provenance and
license, schema validated, data quality profiled, temporal split, leakage-safe features, EDA,
feature selection and PCA, validation comparison, tuning, a validation-frozen operating point, a
single-touch test evaluation, a released model bundle (`models/LATEST`), SHAP/PDP explainability,
and the Bias & Fairness Analysis (Milestones 1–7). The final report and decks follow in Milestone 8. See
`specs/001-aml-risk-triage/tasks.md`.

## Provenance

PaySim (Kaggle `ealaxi/paysim1`), downloaded 2026-09-05 via the Kaggle API, license **CC BY-SA 4.0**
as reported by the dataset metadata, SHA-256 recorded in `configs/data_source.yaml` and verified on
every fetch. Full provenance, attribution, and the schema confirmation are in `data/README.md`.
Raw and processed data are never committed.

## Setup

Requires Python 3.11.12 (`pyenv install 3.11.12`) and [uv](https://github.com/astral-sh/uv).

```bash
make setup            # .venv, pinned dependencies, editable install, pre-commit hooks
source .venv/bin/activate
```

## Commands

```bash
make lint             # ruff check + format check
make test             # pytest
make coverage         # pytest with coverage gate (enforced from task T066)
make ci               # lint + test + tracked-data check + smoke pipeline
make data             # fetch PaySim (Kaggle API if KAGGLE_* set, else manual steps) and verify checksum
python -m aml_triage validate-schema | profile | data-dictionary   # after paths.raw_csv is set
python -m aml_triage --help
```

_Data fetch, pipeline, report, and slide commands are added as their milestones land._

## Repository map

```text
configs/     run configuration (base.yaml, vocabulary.yaml, smoke.yaml; schema/features later)
src/aml_triage/  package: config, cli, utils, and one subpackage per pipeline stage
tests/       pytest suite (config, cli, utils, vocabulary, hardcoded-params, optional isolation)
notebooks/   numbered notebooks that call the package (added from Milestone 2)
data/        README with provenance; raw/ and processed/ are gitignored
models/      persisted model bundles (joblib files gitignored; checksums committed)
reports/     data quality, EDA, comparison, fairness, final report, slides
scripts/     fetch, sample, export, slide-count helpers
deployment/  optional Step 8 (Docker, guide, demo)
docs/        optional Step 8/9 documentation
specs/       Spec Kit constitution-driven specification, plan, and tasks
```

## Results

Selected model: **histogram gradient boosting on the `primary` feature set** (tuned; verdict fixed on
validation before the test split was unlocked). Single-touch test evaluation, steps 553–743,
194,135 rows, 2,120 positives (prevalence 1.09%). Comparators and ablations are in
`reports/model_comparison.md`; the verdict reasoning is in `reports/selection_matrix.md`.

| metric | validation | test (95% bootstrap CI) |
|---|---|---|
| PR-AUC (primary) | 1.0000 | 1.0000 [1.0000, 1.0000] |
| Recall@200 (operational, mean over review periods) | 0.8029 | 0.7568 (pooled CI [0.7252, 0.7866]) |
| Precision@200 | 1.0000 | 1.0000 |
| Random ranking Recall@200 / rule comparator Recall@200 (test) | – | 0.1012 / 0.3101 |

Recall@200 is a ceiling set by capacity: every review period holds more than 200 positives and the
top 200 are all positives, so the model catches 200 per day and the rest wait. **Illustrative** count
on synthetic data: 200 positives surfaced per day versus 83 for the rule comparator and 28 for random
ranking. Near-perfect separability is a property of the PaySim generator, not evidence of real-world
AML capability. No accuracy headline (majority-class accuracy is 0.99).

## Reproducibility tolerance

Measured by `python -m aml_triage reproduce-check` on 2026-09-05 (seed 42, OMP threads 4, n_jobs 4): **Exact.** Two independent refits of the selected model produced identical validation scores and metrics. Max abs score difference between refits: 0.00e+00; vs the released bundle's validation metrics: 0.00e+00. Details in `reports/reproducibility.json`.

## Optional steps

- Step 8 (Deployment & MLOps): not attempted yet.
- Step 9 (Generative AI): not attempted yet. Usage, if any, will be documented in
  `docs/genai_usage.md`.

## Links

- Specification, plan, and tasks: `specs/001-aml-risk-triage/`
- Constitution: `.specify/memory/constitution.md`
- Final report and decks: _added in Milestone 8_
