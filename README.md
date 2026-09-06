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

Milestones 1–8 are complete: scaffold and tooling, PaySim acquired with recorded provenance and
license, schema validated, data quality profiled, temporal split, leakage-safe features, EDA,
feature selection and PCA, validation comparison, tuning, a validation-frozen operating point, a
single-touch test evaluation, a released model bundle (`models/LATEST` = `20260904T225142-0dc8f82-hgb`),
SHAP/PDP explainability, the Bias & Fairness Analysis, the final report, and two slide decks.
Optional Steps 8 and 9 are tracked below. Task list: `specs/001-aml-risk-triage/tasks.md`.

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
make test             # pytest (leakage guards, test-access state machine, vocabulary scan, notebooks compile)
make coverage         # pytest with the coverage gate
make ci               # lint + test + tracked-data check + smoke pipeline
make data             # fetch PaySim (Kaggle API token in .env, or manual steps) and verify SHA-256
python -m aml_triage validate-schema | profile | data-dictionary
make pipeline         # split -> build-features -> select-features -> pca -> train -> compare -> tune
                      # -> choose-operating-point -> freeze -> evaluate --split test (single touch)
                      # -> select -> reproduce-check -> explain -> fairness-availability -> fairness -> build-report
make report           # assemble reports/final_report.md and export final_report.pdf
make slides           # technical deck (reveal.js HTML + PDF) and business deck (PPTX + PDF), slide-count check
make package          # copy report + decks into submission/ (gitignored) under the submission file names
python -m aml_triage --help   # all 22 commands; every command takes --config and --seed
```

The test split can be scored once per configuration. A second `evaluate --split test` is refused
unless `--force-reevaluate --reason "..."` is passed, and the reason is written to
`data/processed/test_access.json`.

The split manifest and that test-access record are tracked in git, so a clean clone starts frozen
and already evaluated. Replaying the pipeline from a clone (the reproducibility check) is therefore
an audited re-evaluation:

```bash
make pipeline EVALUATE_FLAGS='--force-reevaluate --reason "clean-clone reproducibility run"' && make report
```

`split` and `freeze` verify that the recomputed partition and operating point are identical to the
frozen ones and leave the tracked records untouched; any difference is refused (exit 3).

## Repository map

```text
configs/         base.yaml (seed, split, K), schema.yaml, features.yaml (registry), data_source.yaml,
                 vocabulary.yaml, operating_point.yaml (frozen), models/*.yaml (+ *.tuned.yaml)
src/aml_triage/  config, cli, utils; data/ (load, schema, profiling, dictionary, split);
                 features/ (transforms, causal aggregates, pipeline + fit-scope recorder, selection, pca);
                 models/ (registry, comparators, train, tune, lifecycle: freeze/evaluate/select/queue/reproduce);
                 evaluation/ (metrics, capacity, calibration, bootstrap, compare, threshold, capacity_report);
                 explain/ (SHAP, PDP/ICE, captions); fairness/ (availability, slices, demographic, report);
                 eda/, reporting/ (figures, tables, report_builder)
tests/           127 tests: config, CLI, schema, split, features, causal aggregates, leakage + test-access
                 guards, metrics, capacity, training, fairness, vocabulary, notebooks compile, report builder
notebooks/       01–07 numbered notebooks that call the package; 90_technical_deck.ipynb (slides)
data/            README (provenance, license, checksum); raw/ and processed/ gitignored except small
                 governance JSON (split manifest, test-access record, feature lists, fit-scope records)
models/          <version>/ bundle (pipeline.sha256, config snapshot, metrics, feature list, model card); LATEST
reports/         data quality, dictionary, EDA, selection, PCA, comparison, selection matrix, capacity,
                 explainability, Bias & Fairness Analysis, review queues, final_report.md/.pdf, slides/
scripts/         fetch_data.sh, export_report.sh, md_to_html.py, html_to_pdf.py, build_business_deck.py,
                 check_slide_counts.py
specs/           Spec Kit constitution-driven specification, plan, research, data model, contracts, tasks
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

## Clean-clone check

On 2026-09-06 the commands above were run in a fresh clone (data re-downloaded and checksum-verified).
All 301 metric values in the released bundle's `metrics.json` reproduced exactly (only fit seconds and
timestamps differed), the regenerated estimator scores all 181,068 validation rows identically to the
released one, and the split, selected feature set, tuned parameters and sealed operating point were
regenerated identically. `pipeline.joblib` is not byte-identical (the bundle embeds its version string
and a timestamp), so score equality, not the file checksum, is the reproducibility criterion. Details
in the final report's Reproducibility section.

## Optional steps

- **Step 8 (Deployment & MLOps): attempted.** Local FastAPI scoring service (`src/aml_triage/api/`,
  `make api`, contract in `specs/001-aml-risk-triage/contracts/scoring-api.yaml`), Docker image
  (`deployment/Dockerfile`, `make docker-build`), deployment guide (`deployment/DEPLOYMENT.md`),
  demo (`deployment/demo/demo.gif`, a rendered transcript of real responses), MLOps plan
  (`docs/mlops_plan.md`). Cloud deployment not attempted.
- **Step 9 (Generative AI): attempted.** The build was AI-assisted end to end; the record of tools,
  purposes, prompts, outputs, human review, and corrections is `docs/genai_usage.md`.

## Links

- Final report: `reports/final_report.md` (PDF: `reports/final_report.pdf`, self-contained HTML: `reports/final_report.html`)
- Technical deck (11 slides): `reports/slides/technical_deck.html` / `.pdf` (source: `notebooks/90_technical_deck.ipynb`)
- Business deck (10 slides): `reports/slides/business_deck.pptx` / `.pdf` (source outline: `reports/slides/business_deck_outline.md`)
- Model card: `models/20260904T225142-0dc8f82-hgb/model_card.md`
- Bias & Fairness Analysis: `reports/bias_fairness_analysis.md` · Explainability: `reports/explainability.md`
- Selection matrix: `reports/selection_matrix.md` · Capacity analysis: `reports/capacity_analysis.md`
- Specification, plan, and tasks: `specs/001-aml-risk-triage/` · Constitution: `.specify/memory/constitution.md`
