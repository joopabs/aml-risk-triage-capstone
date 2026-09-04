<!--
Sync Impact Report
==================
Version change: (template, unversioned) → 1.0.0
Bump rationale: Initial ratification. The prior file was the unfilled Spec Kit scaffold.

Modified principles: none (all principles newly defined)

Added sections:
- Core Principles I–XI (template scaffold had 5 unnamed placeholder slots; project defines 11)
- Additional Constraints (repository structure, data handling, technology, documentation)
- Quality Gates & Definition of Done
- Governance

Removed sections: none (placeholder slots replaced, not removed)

Templates requiring review (not modified by this command):
- .specify/templates/plan-template.md → Constitution Check section should reference gates G1–G12
- .specify/templates/spec-template.md → no structural change required
- .specify/templates/tasks-template.md → no structural change required

Follow-up TODOs: none. All placeholders resolved.
-->

# Explainable AML Transaction-Risk Triage Constitution

Project: Explainable AML Transaction-Risk Triage for SME and Corporate Banking
Nature: End-to-end, reproducible, responsible machine-learning capstone (Pillar 5)
Dataset: PaySim synthetic financial transactions (Kaggle: ealaxi/paysim1)
Source requirements: `CAPSTONE_BRIEF.md`, `PROJECT_DECISIONS.md`

This constitution governs every specification, plan, task, notebook, script, model,
report, and slide deck produced in this repository. Where it conflicts with convenience,
habit, or a template default, this constitution wins.

## Core Principles

### I. Business-Framed Problem Definition

The project MUST be framed as a decision-support problem before any code is written.

- The problem statement MUST name the business context (AML transaction-risk triage for
  SME and corporate banking), the unit of analysis (one synthetic financial transaction),
  the task type (binary classification on `isFraud`), and the prediction objective
  (assign a risk score to prioritize transactions for human investigator review).
- The primary technical metric is PR-AUC. The operational metric is Recall@K, where K is
  an explicitly stated, illustrative daily investigator-review capacity. Secondary metrics
  (Precision@K, recall, precision, F1, ROC-AUC, confusion matrix, PR curve, calibration
  curve, false-positive rate) MUST be reported alongside, never instead of, the primary and
  operational metrics.
- At least one business KPI MUST be defined and traced to the operational metric (e.g.,
  suspicious transactions prioritized per day and review-efficiency improvement at fixed
  capacity). KPI figures MUST be labeled "illustrative" wherever they appear.
- Accuracy MUST NOT be presented as a headline metric for this imbalanced problem.

Rationale: Rubric criterion 1 rewards business context plus measurable technical and
business KPIs. A triage tool is judged by what it surfaces within capacity, not by
aggregate correctness.

### II. Data Provenance, Licensing & Privacy

Only public or explicitly approved data MAY be used, and its origin MUST be auditable.

- The dataset source URL, download date, file checksum, and the license or usage terms
  shown on the source page at download time MUST be recorded in the data dictionary or
  a `data/README.md`. If the license cannot be verified, the dataset MUST NOT be used.
- PaySim is synthetic mobile-money data. It MUST NOT be described, labeled, or implied to
  be real SME, corporate, or Philippine banking data anywhere in code, reports, or slides.
- Raw data files MUST NOT be committed to Git. `data/raw/` and `data/processed/` MUST be
  gitignored; the repository MUST document the command that reproduces them.
- Credentials, API keys, tokens, personal data, and internal or proprietary information
  MUST NEVER be committed. Secrets, if any are needed for optional work, MUST be loaded from
  environment variables or an untracked `.env` file, with a committed `.env.example`.
- Every commit MUST pass a secret scan (pre-commit hook or CI check) before merge to `main`.

Rationale: Rubric criterion 2 requires a justified, cited dataset. Honest labeling of
synthetic data is a precondition for every limitation statement in the project.

### III. Reproducibility (NON-NEGOTIABLE)

Any reviewer MUST be able to regenerate every reported number, artifact, and figure from
a clean checkout using only documented commands.

- A pinned `requirements.txt` (exact versions) MUST be committed. A Python version MUST be
  declared. Optional Docker or lock files MAY be added but MUST NOT replace `requirements.txt`.
- A single global random seed MUST be defined in configuration and propagated to every
  stochastic component: splitting, resampling, model initialization, hyperparameter search,
  SHAP sampling, and any UMAP/t-SNE visualization.
- All run parameters (paths, seed, split strategy, K for Recall@K, feature lists, model
  hyperparameters) MUST live in versioned config files under `configs/`. Notebooks and
  scripts MUST read from config, not hardcode values.
- Trained models, fitted preprocessing pipelines, metric tables, and the exact config used
  MUST be saved as artifacts under `models/` or `reports/` with a model version identifier.
- Automated tests under `tests/` MUST cover data-loading contracts, feature-engineering
  functions, split-leakage guards, and metric computations. Tests MUST pass in CI or via a
  documented local command before any deliverable is declared complete.
- `README.md` MUST contain the ordered commands to set up the environment, fetch data,
  run the pipeline, run tests, and regenerate reports. These commands MUST be verified on a
  clean environment before submission.

Rationale: Reproducibility is scored in rubric criteria 3, 4, and 7 and is the only defense
against untraceable results.

### IV. Leakage-Safe Splitting & Training-Only Fitting (NON-NEGOTIABLE)

No information from validation or test data MAY influence any fitted component.

- The train/validation/test split MUST be temporal (by PaySim `step`) if temporal ordering
  is used for any feature, and otherwise stratified on `isFraud`. The chosen strategy and
  its justification MUST be documented in the spec and the report.
- The following MUST be fitted on training data only and then applied to validation/test:
  imputation, scaling, encoding, binning thresholds, feature selection, resampling
  (SMOTE/under/over-sampling), PCA, and hyperparameter tuning. Resampling MUST NEVER be
  applied to validation or test data.
- Aggregate features (e.g., prior-transaction counts or sums) MUST be computed causally,
  using only transactions that precede the current one in time. Features derived from
  post-transaction state that would not be available at scoring time MUST be flagged and
  either excluded or explicitly justified.
- Preprocessing MUST be implemented as a fitted pipeline object (e.g., scikit-learn
  `Pipeline`/`ColumnTransformer`) and saved with the model so inference reuses the exact
  training-time transforms.
- At least one automated test MUST assert that no test-set row indices appear in training
  data and that fitted transformers were not exposed to test rows.

Rationale: Leakage inflates every metric and invalidates the model-comparison criterion
(20 points). Rubric criterion 5 explicitly demands leakage be addressed.

### V. Data Quality, EDA & Feature Engineering Rigor

Data MUST be understood and documented before it is modeled.

- A data quality analysis MUST explicitly report: null counts per column, duplicate rows,
  outliers (method stated), invalid values (negative balances, zero-amount transactions,
  balance-arithmetic inconsistencies), class imbalance ratio, and known limitations of the
  source data (synthetic generation, fraud only in certain transaction types, simulator
  artifacts). Findings MUST be tied to concrete handling decisions.
- A complete data dictionary MUST list every variable with type, unit, range or allowed
  values, and description.
- EDA MUST cover univariate distributions, bivariate relationships with the target,
  correlations, and class-conditional differences, with visuals.
- Feature engineering MUST be domain-informed and justified. The initial focus set is:
  transaction type, log amount, origin/destination balance deltas, balance-inconsistency
  flags, amount-to-origin-balance ratio, amount buckets, and causally valid prior-transaction
  aggregates. Every feature MUST have a one-line rationale in the report.
- At least one feature-selection method (filter, wrapper, or embedded) MUST be applied and
  justified, with before/after feature lists recorded.
- PCA MUST be performed and its role stated (dimensionality reduction for modeling,
  visualization, or diagnostic only). If PCA is not used in the final model, the report
  MUST say so and why. t-SNE/UMAP MAY be added for visualization only.

Rationale: Rubric criteria 2 and 3 (20 points combined) require documented handling of
nulls, duplicates, outliers, insightful EDA, creative domain features, and at least one
selection plus one dimensionality-reduction method.

### VI. Baseline Plus Candidates, Evidence-Based Selection

Model choice MUST be argued from evidence against the stated objective, not from accuracy
or novelty.

- A trivial baseline (dummy/majority or prior-rate classifier) MUST be trained and reported
  first. At least three additional appropriate candidates MUST be implemented. The current
  candidate set is: class-weighted logistic regression, balanced random forest, and
  gradient boosting/XGBoost. Deep learning MAY be added only with written justification of
  appropriateness for tabular data of this size.
- Every candidate MUST be evaluated on the same held-out split with the same metric suite
  and the same K. Hyperparameter tuning MUST use training/validation data only.
- Model selection MUST weigh, in writing: PR-AUC, Recall@K and Precision@K at the stated
  capacity, the recall/precision trade-off curve, calibration quality, explainability,
  inference and maintenance risk, and investigator workload. A selection matrix MUST appear
  in the report. Accuracy alone MUST NOT decide selection.
- The chosen decision threshold or top-K rule MUST be stated and justified against
  investigator capacity.
- Model comparison tables MUST include confidence intervals or repeated-seed variance where
  computationally feasible; if omitted, the omission MUST be stated.

Rationale: Rubric criterion 4 (20 points) requires multiple tuned models, correctly applied
metrics, saved artifacts, and clear reasoning for the choice.

### VII. Explainability

Every deployed or recommended model MUST be explainable at global and local levels.

- Global explanations (SHAP summary/importance) and local explanations (SHAP per-transaction
  waterfall or force plots) MUST be produced for the selected model.
- PDP and/or ICE plots MUST be produced for the top features where the method is technically
  valid (e.g., not for strongly correlated feature pairs without caveat). Where invalid or
  misleading, the report MUST state why and offer a documented alternative (LIME, permutation
  importance, or model-native importances).
- Explanations MUST be checked for consistency with domain reasoning and the EDA. Surprising
  attributions MUST be discussed, not hidden.
- Any explainability output shown to a "business" audience MUST be translated into plain
  language with its limitations stated.

Rationale: Rubric criterion 5 scores explainability tooling; a triage tool that
investigators cannot interrogate is not fit for human-in-the-loop use.

### VIII. Ethical AI, Fairness & Honest Limitations (NON-NEGOTIABLE)

The project MUST include a Bias & Fairness Analysis and MUST NOT overstate what synthetic
data can prove.

- Sensitive attributes (age, gender, ethnicity, nationality, socioeconomic status) MUST NOT
  be assumed present. Their availability MUST be verified during profiling and the result
  recorded.
- If valid sensitive-group labels exist, demographic fairness metrics (demographic parity,
  equalized odds, disparate impact) MUST be computed and mitigations proposed.
- If they do not exist (expected for PaySim), the report MUST state plainly that demographic
  fairness cannot be measured on this dataset. The project MUST then conduct operational
  error-slice analysis (e.g., by transaction type, amount bucket, balance band, time step)
  and MUST label it "operational error-slice analysis". It MUST NOT be called demographic
  fairness, bias audit by protected group, or any equivalent term.
- A governance-controlled fairness audit plan for any real-world use MUST be proposed,
  naming the data, metrics, owners, and review cadence that would be required.
- Limitations MUST be discussed explicitly: class imbalance and its handling, leakage risks
  and controls, overfitting evidence, synthetic-label validity, simulator artifacts, and
  transferability to real banking data. The report MUST state that results cannot establish
  actual fraud/AML detection effectiveness, fairness, or regulatory suitability.
- Proposed mitigations (reweighting, threshold adjustment, augmentation, post-processing,
  monitoring) MUST be concrete and feasible for the stated deployment context.

Rationale: Rubric criterion 5 (20 points) requires a bias audit, fairness metrics, and
mitigations. Honesty about what cannot be measured scores higher than fabricated metrics
and is a professional obligation in an AML context.

### IX. Human-in-the-Loop Decision Support Only (NON-NEGOTIABLE)

The system is an educational prototype that prioritizes review. It MUST NEVER make or
imply a determination.

- Outputs are limited to: a risk score, a review-priority recommendation, the model version,
  and an educational disclaimer. Any API, dashboard, notebook cell, or slide that presents
  outputs MUST include the disclaimer.
- The project MUST NOT implement, simulate, or describe as available: automatic transaction
  blocking, account closure, customer risk rating, suspicious-activity or regulatory filing,
  or any actual AML determination.
- Terminology MUST be consistent: "flagged for review", "prioritized", "risk score". Words
  such as "fraudulent", "launderer", "guilty", or "confirmed" MUST NOT be applied to model
  outputs. "Simulated fraud" is the correct term for the positive label.
- The final report and business deck MUST describe the intended human review workflow,
  investigator role, and override capability.

Rationale: Misuse of a triage score as a determination causes real harm and regulatory
exposure. The project's value proposition is decision support, not automation.

### X. Communication & Repository Professionalism

Deliverables MUST be complete, audience-appropriate, and professionally structured.

- Two slide decks MUST be produced, each 8–12 slides: a technical deck (methodology,
  visuals, metrics; Jupyter slides or LaTeX Beamer or equivalent) for peers, and a
  business-facing deck (ROI framed as illustrative, risks, strategy, human-in-the-loop
  model) for non-technical executives.
- A final report MUST be produced containing, at minimum: problem statement, dataset
  overview and data dictionary, EDA + Feature Engineering Report, model comparison and
  selection, Bias & Fairness Analysis, limitations, and reproducibility instructions.
- The repository MUST be public and structured as: `src/` (importable package and CLI
  scripts), `notebooks/` (numbered, executed top-to-bottom, outputs cleared or committed
  consistently), `data/` (gitignored raw/processed plus `README.md`), `models/`,
  `reports/` (report, figures, decks), `tests/`, `configs/`, `README.md`,
  `requirements.txt`, `.gitignore`, and a license file.
- Commit history MUST be clean and descriptive, using conventional prefixes
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `data:`, `model:`). Force-pushes to `main`
  are prohibited. Work MUST proceed on feature branches merged via reviewed pull requests
  or squash merges with meaningful messages.
- `README.md` MUST include: project purpose and disclaimer, dataset provenance, setup and
  run commands, repository map, results summary with the primary and operational metrics,
  and links to the report and decks.

Rationale: Rubric criteria 6 and 7 (25 points combined) reward two high-quality decks,
open-source structure, README, `requirements.txt`, and clean commit history.

### XI. Transparent Optional Work

Optional deliverables MUST be honestly scoped and never inflate the core claims.

- Optional Step 8 (Deployment & MLOps) MAY be attempted. If attempted, a local FastAPI (or
  Flask/Dash) deployment is REQUIRED. It MUST load the saved pipeline and model artifact,
  return score, review-priority recommendation, model version, and disclaimer, and ship with
  a deployment guide and demo media (GIF/screencast). Docker, MLflow/W&B tracking, CI
  checks, a monitoring plan, and a versioning/rollback plan MAY be added and MUST be
  documented if present.
- Optional Step 9 (Generative AI) MAY be attempted. If any GenAI tool is used for code,
  EDA summaries, data dictionaries, or documentation, the report MUST record: the tool and
  model, the purpose, representative prompts and outputs, the human review performed, and
  known limitations or errors found. GenAI-produced text MUST be verified against actual
  outputs before inclusion.
- Optional work MUST be clearly separated in the repository (e.g., `src/api/`,
  `deployment/`, `docs/genai_usage.md`) and MUST NOT be a dependency for reproducing the
  core pipeline and report.
- The README and decks MUST state which optional steps were attempted and which were not.

Rationale: Steps 8 and 9 count toward the 5 bonus points inside the 100-point total.
Transparent scoping protects the core deliverables and the project's credibility.

## Additional Constraints

**Repository structure (required at submission):**

```
.
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── .env.example                 # only if optional work needs env vars
├── configs/                     # YAML/JSON run configs, seed, K, paths
├── data/
│   ├── README.md                # provenance, license, checksum, fetch command
│   ├── raw/                     # gitignored
│   └── processed/               # gitignored
├── notebooks/                   # 01_..., 02_... executed in order
├── src/                         # importable package + CLI entry points
├── models/                      # saved pipelines, models, model card/version
├── reports/
│   ├── final_report.(md|pdf)
│   ├── figures/
│   └── slides/                  # technical + business decks
├── tests/
└── deployment/ or src/api/      # optional Step 8 only
```

**Technology and environment:**

- Python 3.x with version pinned in `README.md` and, if used, `pyproject.toml`/`runtime.txt`.
- Core stack: pandas, numpy, scikit-learn, imbalanced-learn, XGBoost (or LightGBM with
  justification), SHAP, matplotlib/seaborn, pytest. Additional libraries MUST be justified
  in the plan and pinned.
- All figures MUST be regenerated by code under `src/` or `notebooks/`; no hand-edited
  images in `reports/figures/`.

**Data handling:**

- Raw PaySim CSV is fetched by a documented command, checksummed, and never modified in
  place. Processed datasets are derived artifacts and reproducible from raw plus config.
- No row-level data appears in slides or the report beyond small, clearly synthetic
  illustrative examples.

**Documentation language:**

- Every quantitative business claim is prefixed or footnoted as "illustrative".
- Every model-output description uses triage vocabulary per Principle IX.
- The educational disclaimer text is defined once in `configs/` or `src/` and reused
  verbatim across API, notebooks, report, and decks.

## Quality Gates & Definition of Done

Each gate MUST be satisfied and evidenced (file path, test name, or report section) before
the corresponding phase is marked complete in `tasks.md`. The plan's Constitution Check
MUST enumerate these gates.

| Gate | Requirement | Evidence |
|------|-------------|----------|
| G1 Framing | Problem statement, task type, unit of analysis, PR-AUC primary, Recall@K with stated K, business KPI labeled illustrative | `spec.md`, report §1 |
| G2 Provenance | Source URL, download date, checksum, license recorded; synthetic nature stated; raw data gitignored; secret scan passing | `data/README.md`, pre-commit/CI log |
| G3 Reproducibility | Pinned `requirements.txt`; global seed in config; artifacts saved with version; README commands verified on clean env | `configs/`, `models/`, README, CI run |
| G4 Leakage | Split strategy documented; all fitting on train only; causal aggregates; leakage test passing | `tests/test_split_leakage.py`, report §3 |
| G5 Data quality | Nulls, duplicates, outliers, invalid values, imbalance ratio, source limitations reported with handling decisions; full data dictionary | report §2, `reports/data_dictionary.*` |
| G6 EDA & FE | Univariate/bivariate/correlation EDA with visuals; every feature has rationale; ≥1 feature-selection method; PCA performed and role stated | report §3, `notebooks/` |
| G7 Models | Dummy baseline + ≥3 candidates; same split, metric suite, and K; selection matrix covering PR-AUC, Recall@K, Precision@K, calibration, explainability, risk, capacity | report §4, `reports/model_comparison.*` |
| G8 Explainability | SHAP global + local for selected model; PDP/ICE or documented alternative; plain-language translation | report §5, `reports/figures/` |
| G9 Ethics & fairness | Sensitive-attribute availability verified; demographic metrics computed OR limitation stated and operational error-slice analysis labeled as such; audit plan; mitigations; limitations section | report §6 "Bias & Fairness Analysis" |
| G10 Human-in-the-loop | Disclaimer present on every output surface; prohibited actions absent; triage vocabulary audited | grep of repo, API schema, decks |
| G11 Communication | Technical deck 8–12 slides; business deck 8–12 slides; final report complete; README complete | `reports/slides/`, `reports/final_report.*` |
| G12 Optional transparency | Attempted/not-attempted status of Steps 8 and 9 stated; if attempted, deliverables and documentation present | README, `docs/genai_usage.md`, `deployment/` |

**Definition of Done (project level):**

The capstone is DONE only when all of the following are true:

1. Gates G1–G12 are satisfied with evidence linked from `README.md` or the final report.
2. `pytest` passes and the full pipeline runs end-to-end from a clean clone using only
   README commands, regenerating every metric and figure cited in the report and decks.
3. The public GitHub repository matches the required structure and has no committed data,
   secrets, or credentials (verified by secret scan and `.gitignore` review).
4. Final report, technical deck, and business deck are exported in an approved submission
   format (`.pdf`, `.doc`, `.pptx`, or `.ppt`) and named per the submission instructions
   (`Your_Name_Assignment name`).
5. Every rubric criterion (1–7) has been self-assessed against its "Outstanding/Exemplary"
   descriptors in a checklist committed to `reports/` or the README, with gaps either closed
   or explicitly acknowledged.
6. No statement in any deliverable claims real-world AML effectiveness, real-data
   applicability, or demographic fairness beyond what the evidence supports.

**Definition of Done (task level):** a task is complete when its code is tested, its output
artifact is saved under the correct directory, its config is committed, and the relevant
gate row can cite it as evidence.

## Governance

This constitution supersedes all other practices, templates, and conventions in this
repository. Specifications, plans, and task lists MUST include a Constitution Check that
maps their content to the principles and gates above; any violation MUST be justified in
writing and approved before implementation proceeds.

**Amendment procedure:**

1. Propose the change as a pull request modifying only `.specify/memory/constitution.md`,
   with the rationale in the PR description.
2. Update the Sync Impact Report comment at the top of the file.
3. Bump the version per the policy below and update **Last Amended**.
4. Review dependent templates and open artifacts (`spec.md`, `plan.md`, `tasks.md`) for
   required propagation and record follow-ups in the Sync Impact Report.

**Versioning policy (semantic):**

- MAJOR: removing or redefining a principle, gate, or prohibition in a backward-incompatible
  way (e.g., relaxing Principle IX or IV).
- MINOR: adding a principle, gate, or materially expanded guidance.
- PATCH: clarifications, wording, and non-semantic fixes.

**Compliance review:**

- Every pull request MUST state which gates it advances and confirm no principle is violated.
- Before each Spec Kit phase transition (specify → plan → tasks → implement), the
  Constitution Check MUST be re-run against the current artifact.
- Before submission, a full G1–G12 review MUST be recorded in the repository.
- Runtime development guidance for agents lives in `CLAUDE.md` if present; it MUST NOT
  contradict this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-09-04 | **Last Amended**: 2026-09-04
