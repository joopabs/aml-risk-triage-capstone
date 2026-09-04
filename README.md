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

Milestone 1 of 9 (repository scaffold, configuration, quality tooling, starter tests) is complete.
No data has been downloaded, no model trained, and no results exist yet. See
`specs/001-aml-risk-triage/tasks.md` for the plan.

## Provenance

_To be completed in Milestone 2 (task T017)._ Source URL, download date, SHA-256 checksum, and the
verbatim license text will be recorded here and in `data/README.md` and
`configs/data_source.yaml`. Raw and processed data are never committed.

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

_Not available yet._ Primary metric: PR-AUC. Operational metric: Recall@K at an illustrative
daily review capacity K set in `configs/base.yaml` after profiling. No accuracy headline.

## Reproducibility tolerance

_To be recorded by `python -m aml_triage reproduce-check` (task T062)._

## Optional steps

- Step 8 (Deployment & MLOps): not attempted yet.
- Step 9 (Generative AI): not attempted yet. Usage, if any, will be documented in
  `docs/genai_usage.md`.

## Links

- Specification, plan, and tasks: `specs/001-aml-risk-triage/`
- Constitution: `.specify/memory/constitution.md`
- Final report and decks: _added in Milestone 8_
