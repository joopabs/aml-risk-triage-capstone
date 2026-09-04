# Feature Specification: Explainable AML Transaction-Risk Triage

**Feature Branch**: `001-aml-risk-triage`

**Created**: 2026-09-04

**Status**: Draft

**Input**: User description: "Create a complete feature specification for the PaySim-based
'Explainable AML Transaction-Risk Triage for SME and Corporate Banking' capstone. The model
must rank synthetic transactions for investigator review; it must not automatically block
transactions or make real AML determinations." (Full input retained in the invoking command;
source documents: `CAPSTONE_BRIEF.md`, `PROJECT_DECISIONS.md`, `.specify/memory/constitution.md`.)

**Governing constitution**: v1.0.0. Every requirement below maps to one or more constitution
principles (I–XI) and quality gates (G1–G12). Mappings are noted inline as `[P#]` / `[G#]`.

**Placeholder convention**: Values that require dataset profiling, license inspection, or model
evaluation are written as `[PROFILE: …]`, `[VERIFY: …]`, or `[MEASURED: …]`. They MUST be
resolved by the validation tasks in the "Validation Tasks & Placeholders" section. No dataset
statistic, feature list, sensitive attribute, model score, financial impact, or fairness result
in this document is asserted as fact.

## Business Context & Scope

### Problem statement

Banks serving small-and-medium enterprise (SME) and corporate clients monitor large volumes of
payment transactions for possible money-laundering or fraud indicators. Investigator capacity is
fixed and far smaller than transaction volume, so most alerts are never reviewed in depth and
many reviewed alerts are false positives. The capstone builds an educational decision-support
prototype that assigns each transaction a risk score and ranks transactions so that a limited
number of daily investigator reviews is spent on the transactions most likely to warrant
attention.

The prototype is trained and evaluated on PaySim, a public synthetic mobile-money dataset with
a simulated fraud label. PaySim is used as a stand-in because real SME/corporate transaction
data with labels is not publicly available. All results are therefore about simulated fraud in
synthetic data and MUST be described as such. [P II, VIII]

### Stakeholders

| Stakeholder | Role in this project | What they need |
|-------------|---------------------|----------------|
| AML/financial-crime investigator (simulated end user) | Consumes the ranked review queue | A short, ranked list with a plain-language reason per item and the ability to override |
| Compliance / financial-crime operations lead (business owner) | Sets review capacity K, owns the illustrative KPI | Evidence that ranking improves review efficiency at fixed capacity; clear statement of risks |
| Model risk / governance reviewer | Assesses fairness, limitations, and misuse controls | Honest fairness-data check, leakage controls, limitations, mitigation plan, human-in-the-loop design |
| Data scientist / technical peer (and capstone grader) | Reproduces and audits the work | Reproducible pipeline, model comparison, explainability, tests, clean repository |
| Executive audience | Consumes the business deck | Illustrative ROI framing, risks, strategy, and what the tool does NOT do |
| Learner (project author) | Delivers the capstone | Rubric coverage against the "Outstanding/Exemplary" band |

### Intended decision

**Which transactions, out of all transactions in a review period, should an investigator look at
first, given a fixed capacity of K reviews?** The system outputs a ranked list. A human decides
what, if anything, to do with each reviewed transaction.

### Intended use

- Educational decision-support prototype for review prioritization on synthetic data.
- Demonstration of an end-to-end, reproducible, explainable, responsibly framed ML lifecycle.
- Inputs to a human review workflow: risk score, review-priority recommendation, model version,
  per-transaction explanation, and an educational disclaimer. [P IX]

### Explicit non-use

The system MUST NOT, and MUST NOT be described as able to: [P IX]

- automatically block, hold, delay, or reverse transactions;
- close, freeze, or restrict accounts;
- assign a customer- or entity-level risk rating;
- generate, recommend, or file suspicious-activity or any regulatory report;
- make an actual AML, fraud, or money-laundering determination;
- be used on real customer data without a governance-controlled validation and fairness audit.

The positive label is "simulated fraud". Model outputs are "risk scores" and "review
priorities". The words "fraudulent", "launderer", "guilty", or "confirmed" MUST NOT be applied
to model outputs anywhere in code, report, or slides.

### Task definition

| Item | Definition |
|------|------------|
| Unit of analysis | One synthetic financial transaction (one row of PaySim) |
| Task type | Binary classification producing a probability-like risk score, used for ranking |
| Target | `isFraud` (1 = simulated fraudulent transaction, 0 = simulated normal transaction) |
| Prediction time | The moment a transaction is observed, using only information available at or before that moment |
| Primary technical metric | PR-AUC (area under the precision-recall curve) on the held-out test set |
| Operational metric | Recall@K: share of all simulated-fraud transactions in the review period that appear in the top K ranked transactions |
| Review capacity K | An illustrative daily investigator capacity, set in configuration. `[VERIFY: choose K after profiling the number of transactions per time step so K is a plausible fraction of daily volume]` |
| Secondary metrics | Precision@K, precision, recall, F1, ROC-AUC, confusion matrix at the chosen operating point, precision-recall curve, calibration curve and a calibration error statistic, false-positive rate |
| Business KPI (illustrative) | Number of simulated-fraud transactions surfaced within K daily reviews, and the relative improvement in that number versus (a) random selection and (b) a simple rule baseline, at the same K. All KPI figures are labeled "illustrative" and MUST NOT be converted to currency or real-world savings. |

### Prediction-time assumptions and temporal leakage controls [P IV]

- Each transaction is scored using only its own fields and aggregates of transactions that
  occurred strictly earlier in time (by PaySim `step`).
- Post-transaction state that would not be known at scoring time is treated as suspect. Each
  such field is either excluded or explicitly justified. `[VERIFY: confirm at profiling which
  balance fields reflect post-transaction state and whether the simulator's balance updates are
  consistent for each transaction type]`
- The rule-based flag column in PaySim, if present, is NOT used as a model feature. It is
  retained only as a rule-baseline comparator. `[VERIFY: confirm the column exists and how often
  it fires]`
- Train / validation / test splits are temporal by `step`, so that all test transactions occur
  after all training transactions. If temporal splitting proves infeasible after profiling
  (for example, no simulated fraud in the later steps), the fallback is stratified splitting
  with all time-derived aggregate features removed, and the report MUST explain the change.
- Every fitted transformation (imputation, encoding, scaling, binning thresholds, resampling,
  feature selection, PCA, hyperparameter tuning) is fitted on training data only.

### False-positive / false-negative trade-offs

| Error | Meaning here | Cost framing (qualitative, illustrative) |
|-------|--------------|------------------------------------------|
| False positive (normal transaction ranked in top K) | An investigator spends a review slot on a benign transaction | Wasted capacity, reviewer fatigue, customer friction if any downstream action were taken (none is taken by this system) |
| False negative (simulated-fraud transaction ranked below K) | A transaction that warranted review is not reviewed that day | Missed opportunity; in real AML the dominant regulatory and reputational risk |

The ranking objective prioritizes recall within capacity. The report MUST show the recall/
precision curve across K, discuss where the trade-off becomes unfavorable, and state that no
threshold in this project has real-world cost validation. Costs are never expressed in
currency.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ranked review queue at fixed capacity (Priority: P1)

A compliance operations lead sets a daily review capacity K. For each review period in the
held-out test data, the system ranks transactions by risk score and produces the top-K list.
The lead sees how many simulated-fraud transactions the list captures compared with random
selection and a simple rule baseline at the same K.

**Why this priority**: This is the core value proposition and the operational metric. Without
a ranked list evaluated at capacity, nothing else in the project has a purpose.

**Independent Test**: Run the evaluation on the held-out test set with a configured K; the
output is a Recall@K and Precision@K table for the selected model, the dummy baseline, random
selection, and the rule baseline, plus the top-K list for at least one review period. Delivers
the illustrative business KPI.

**Acceptance Scenarios**:

1. **Given** a trained, selected model and a held-out test set split temporally, **When** the
   evaluation runs with capacity K from configuration, **Then** the system produces Recall@K
   and Precision@K for the selected model and every comparator, and the selected model's
   Recall@K is greater than that of random selection and the dummy baseline, whose constant
   scores rank as chronological order under the tie-break.
2. **Given** the same inputs, **When** the top-K list for a review period is generated, **Then**
   each list item shows a risk score, rank, review-priority recommendation, model version, and
   the educational disclaimer, and contains no determination language.
3. **Given** a review period with fewer than K transactions, **When** the list is generated,
   **Then** all transactions in the period are listed and the shortfall is reported, not
   padded.

---

### User Story 2 - Reproducible end-to-end pipeline (Priority: P2)

A technical peer or grader clones the public repository, follows the documented commands, and
regenerates every metric, table, and figure cited in the report and decks, obtaining identical
numbers because seeds and configurations are fixed.

**Why this priority**: Reproducibility is a constitutional non-negotiable and underpins the
model-comparison, preprocessing, and repository rubric criteria. It is what makes the P1
claims auditable.

**Independent Test**: From a clean environment, run setup, data fetch, pipeline, tests, and
report regeneration using only README commands. Compare regenerated metric tables to committed
ones.

**Acceptance Scenarios**:

1. **Given** a clean clone and a fresh environment, **When** the documented commands are run in
   order, **Then** the pipeline completes without manual intervention and regenerates all
   reported metrics and figures.
2. **Given** two runs with the same configuration and seed, **When** their metric tables are
   compared, **Then** they are identical (or identical within a documented tolerance for any
   non-deterministic library component, with that tolerance stated).
3. **Given** the repository, **When** the automated tests run, **Then** all tests pass,
   including the leakage guard, schema check, feature-function, and metric-computation tests.
4. **Given** the repository, **When** it is scanned, **Then** it contains no raw or processed
   data files, no credentials, and no secrets.

---

### User Story 3 - Explain why a transaction was prioritized (Priority: P3)

An investigator selects a transaction from the top-K list and sees which features pushed its
risk score up or down, in plain language. A technical reviewer sees global feature importance
and, where valid, how the score responds to changes in the most important features.

**Why this priority**: Investigators cannot responsibly act on, or override, a score they
cannot interrogate. Explainability is also a scored rubric item.

**Independent Test**: For the selected model, generate a global importance summary, at least
three local explanations for top-ranked transactions, and PDP/ICE plots for the top features
where technically valid, each with a plain-language caption.

**Acceptance Scenarios**:

1. **Given** the selected model and the test set, **When** global explanations are generated,
   **Then** a ranked feature-importance summary exists and its top features are discussed
   against the EDA and domain reasoning in the report.
2. **Given** a transaction in the top-K list, **When** a local explanation is requested,
   **Then** the contribution of each feature to that transaction's score is shown with a
   plain-language sentence and the disclaimer.
3. **Given** a top feature for which a partial-dependence view would be misleading (for
   example, strongly correlated with another feature), **When** explanations are produced,
   **Then** the report states why the view is omitted or caveated and names the alternative
   used.

---

### User Story 4 - Ethical AI, fairness-data check, and limitations (Priority: P4)

A model-risk reviewer reads a "Bias & Fairness Analysis" section that first states whether the
dataset contains any valid sensitive-group labels, then either reports demographic fairness
metrics (if labels exist) or states plainly that demographic fairness cannot be measured and
presents a clearly labeled operational error-slice analysis instead, followed by limitations
and a governance-controlled mitigation and audit plan.

**Why this priority**: The rubric's highest-weighted ethical criterion, and a professional
obligation in AML. Honest scoping protects against overclaiming.

**Independent Test**: Read the section and confirm the availability check, the correctly
labeled analysis, the limitations list, and the mitigation plan are all present and that no
operational slice is described as demographic fairness.

**Acceptance Scenarios**:

1. **Given** the profiled dataset, **When** the sensitive-attribute availability check runs,
   **Then** the report records, per candidate attribute (age, gender, ethnicity, nationality,
   socioeconomic status, or any proxy), whether a valid label exists. `[PROFILE: expected
   result is that none exist; do not assume]`
2. **Given** that no valid sensitive-group labels exist, **When** the fairness section is
   written, **Then** it states that demographic fairness metrics cannot be computed, presents
   error rates and Recall@K by operational slices (transaction type, amount band, balance band,
   time step band, and any other non-protected slice), labels the analysis "operational
   error-slice analysis", and proposes a governance-controlled fairness audit for any real use.
3. **Given** that valid sensitive-group labels do exist, **When** the fairness section is
   written, **Then** demographic parity, equalized odds, and disparate impact are reported with
   mitigations proposed.
4. **Given** the report, **When** the limitations subsection is read, **Then** it addresses
   class imbalance handling, leakage controls, overfitting evidence, synthetic-label validity,
   simulator artifacts, and non-transferability to real banking data.

---

### User Story 5 - Communicate to two audiences (Priority: P5)

Peers receive a technical deck covering methodology, visuals, and metrics. Executives receive a
business deck covering the problem, the illustrative KPI, risks, the human-in-the-loop
operating model, what the tool does not do, and a strategy for what a real deployment would
require. Both decks are 8–12 slides. A final report ties everything together.

**Why this priority**: Two decks and a final report are required deliverables, but they depend
on P1–P4 being complete.

**Independent Test**: Count slides, check each deck against its audience checklist, and confirm
the report contains every required section.

**Acceptance Scenarios**:

1. **Given** the completed analysis, **When** the technical deck is reviewed, **Then** it has
   8–12 slides and covers problem framing, data, preprocessing, features, split methodology,
   model comparison, selection rationale, explainability, fairness/limitations, and
   reproducibility.
2. **Given** the completed analysis, **When** the business deck is reviewed, **Then** it has
   8–12 slides, uses no unexplained technical terms, labels every number as illustrative,
   states the non-use list, and presents risks and next steps.
3. **Given** the final report, **When** its table of contents is checked, **Then** it contains
   problem statement, dataset overview and data dictionary, EDA + feature engineering report,
   model comparison and selection, explainability, Bias & Fairness Analysis, limitations, and
   reproducibility instructions.

---

### User Story 6 - Optional local scoring demo (Priority: P6, optional Step 8)

A demo user submits one transaction's fields to a locally running service and receives a risk
score, review-priority recommendation, model version, and disclaimer. The service reuses the
saved training-time preprocessing and model artifact.

**Why this priority**: Optional under the assignment; contributes to bonus points. Must not
become a dependency for the core pipeline.

**Independent Test**: Start the service locally, submit a valid request and an invalid one,
and confirm the responses and the presence of the disclaimer. Record a short demo.

**Acceptance Scenarios**:

1. **Given** the service is running with the saved artifact, **When** a valid transaction
   payload is submitted, **Then** the response contains score, review-priority recommendation,
   model version, and disclaimer, and nothing resembling a block/allow decision.
2. **Given** the service is running, **When** a payload with a missing or invalid field is
   submitted, **Then** the service returns a clear validation error and does not score.
3. **Given** the repository, **When** the optional service code is removed, **Then** the core
   pipeline, tests, and report still run.

---

### User Story 7 - Optional Generative AI usage record (Priority: P7, optional Step 9)

If any generative-AI tool is used for code, EDA summaries, data dictionaries, or prose, the
reader finds a record of the tool, purpose, representative prompts and outputs, the human
review performed, and errors found.

**Why this priority**: Optional under the assignment; contributes to bonus points. Transparency
requirement regardless of scope.

**Independent Test**: Read the GenAI usage document and confirm each field is present for each
use, or a statement that GenAI was not used.

**Acceptance Scenarios**:

1. **Given** GenAI was used, **When** the usage document is read, **Then** every use lists tool
   and model, purpose, representative prompt and output, human review performed, and known
   limitations or corrections.
2. **Given** GenAI produced any text that appears in deliverables, **When** that text is
   checked, **Then** every factual claim in it is traceable to an actual pipeline output.

---

### Edge Cases

- **Transaction types with no simulated fraud in training**: the model must still score them;
  the report must note which types carry all positives. `[PROFILE: distribution of isFraud by
  type]`
- **Zero-amount, negative, or arithmetically inconsistent balances**: must be detected in data
  quality checks and either flagged as features, corrected, or excluded with justification.
- **Account identifiers unseen in training**: identifiers must not be used as direct features;
  only aggregates derived from earlier transactions may reference them.
- **Review period with fewer than K transactions**: list everything, report the shortfall.
- **Tied risk scores at the K boundary**: apply a documented deterministic tie-break (for
  example, earlier timestamp first) so the top-K list is reproducible.
- **Degenerate model output** (constant scores, all-zero probabilities): evaluation must detect
  and report it rather than produce misleading metrics.
- **Schema drift**: if the downloaded dataset lacks an expected column or has an unexpected
  type, the pipeline must stop with a clear schema error before any modeling.
- **License or source page change**: if the recorded license cannot be re-verified, the report
  must flag it and the data must not be redistributed.
- **Later time steps with distribution shift**: temporal test performance may differ from
  validation; the report must show both and discuss shift rather than re-tune on test.
- **Duplicate rows**: exact and near-duplicates must be counted and a handling decision
  recorded before splitting.
- **Resampling leakage**: any synthetic minority samples must exist only in training folds;
  a test must assert this.

## Requirements *(mandatory)*

### Functional Requirements

#### A. Framing and metrics [P I] [G1]

- **FR-001**: The project MUST document the problem statement, stakeholders, intended decision,
  intended use, and explicit non-use exactly as defined in "Business Context & Scope".
- **FR-002**: The project MUST define the task as binary classification on `isFraud` with the
  transaction as unit of analysis, and MUST use the score for ranking rather than as a
  determination.
- **FR-003**: The project MUST report PR-AUC as the primary metric and Recall@K as the
  operational metric, with K read from configuration and stated wherever Recall@K appears.
- **FR-004**: The project MUST report precision, recall, F1, ROC-AUC, confusion matrix at the
  selected operating point, precision-recall curve, calibration curve with a calibration error
  statistic, false-positive rate, and Precision@K for every candidate model on the same split.
- **FR-005**: The project MUST define and compute the illustrative business KPI (simulated-fraud
  transactions surfaced within K reviews and relative improvement over random and rule
  baselines) and label every KPI figure "illustrative". KPI figures MUST NOT be expressed in
  currency or as real-world savings.
- **FR-006**: The project MUST present the false-positive/false-negative trade-off across K and
  discuss its operational implications qualitatively.
- **FR-007**: Accuracy MUST NOT be used as a headline or selection metric; if reported, it
  MUST be accompanied by the class prevalence to show the majority-class baseline.

#### B. Data provenance, licensing, and privacy [P II] [G2]

- **FR-010**: The project MUST record the dataset source URL, download date, file checksum, and
  the license or usage terms displayed on the source page at download time. `[VERIFY: license
  text on the Kaggle dataset page at download time]`
- **FR-011**: If the license cannot be verified or does not permit the intended educational use,
  the dataset MUST NOT be used and the project MUST stop pending an alternative.
- **FR-012**: All documentation MUST describe PaySim as synthetic mobile-money transaction data
  and MUST NOT describe or imply it to be real SME, corporate, or Philippine banking data.
- **FR-013**: Raw and processed data files MUST NOT be committed to version control; a
  documented command MUST reproduce them.
- **FR-014**: No credentials, tokens, personal data, or proprietary information MAY be
  committed; a secret scan MUST run before each merge to the main branch.
- **FR-015**: No row-level data MAY appear in the report or decks beyond small, clearly labeled
  synthetic illustrative examples.

#### C. Schema, data quality, and data dictionary [P V] [G5]

- **FR-020**: The pipeline MUST validate the dataset schema (expected columns, types, and
  non-null constraints) before any processing and MUST fail with a clear error on mismatch.
  `[VERIFY: expected column list and types from the Kaggle dataset page and first-load
  inspection; do not hardcode until confirmed]`
- **FR-021**: The project MUST produce a data quality report covering: row count; null counts
  per column; exact and near-duplicate rows; outliers with the detection method stated;
  invalid values (negative amounts or balances, zero amounts, balance-arithmetic
  inconsistencies per transaction type); class imbalance ratio; and known source-data
  limitations. `[PROFILE: all values]`
- **FR-022**: Every data quality finding MUST be tied to a recorded handling decision
  (keep, correct, flag as feature, exclude) with justification.
- **FR-023**: The project MUST publish a complete data dictionary listing every raw and
  engineered variable with type, unit, range or allowed values, description, and whether it is
  available at prediction time.

#### D. EDA and feature engineering [P V] [G6]

- **FR-030**: EDA MUST include univariate distributions, bivariate relationships with the
  target, correlations, class-conditional comparisons, and behavior over time steps, with
  figures regenerated by code.
- **FR-031**: Feature engineering MUST be domain-informed. The initial candidate set to
  evaluate is: transaction type encoding, log-transformed amount, origin and destination
  balance deltas, balance-inconsistency flags, amount-to-origin-balance ratio, amount buckets,
  and causally computed prior-transaction aggregates. Each retained feature MUST have a
  one-line rationale and a prediction-time availability statement. `[VERIFY: which candidate
  features are computable and informative after profiling]`
- **FR-032**: Aggregate features MUST use only transactions strictly earlier in time than the
  transaction being scored.
- **FR-033**: Raw account identifiers MUST NOT be used as model features.
- **FR-034**: At least one feature-selection method (filter, wrapper, or embedded) MUST be
  applied, fitted on training data only, with before/after feature lists and justification
  recorded.
- **FR-035**: Principal component analysis MUST be performed, fitted on training data only,
  with its role stated (input to a model, diagnostic, or visualization). If PCA components are
  not used by the selected model, the report MUST state so and why.
- **FR-036**: Class imbalance handling (class weighting, resampling, or both) MUST be chosen
  per model, documented, and applied to training data only.

#### E. Splitting, tuning, and leakage controls [P IV] [G4]

- **FR-040**: The primary split MUST be temporal by time step into training, validation, and
  test sets, with all test transactions later than all validation transactions and all
  validation transactions later than all training transactions. Split boundaries MUST be
  recorded in configuration.
- **FR-041**: If the temporal split is infeasible after profiling, the fallback MUST be a
  stratified split with all time-derived aggregate features removed, and the change MUST be
  documented with reasons.
- **FR-042**: All fitted transformations and hyperparameter searches MUST use training data
  (and validation data for model selection) only; the test set MUST be touched exactly once
  per final model for reporting.
- **FR-043**: An automated test MUST assert that no test-set row appears in training or
  validation data, that fitted transformers were fitted only on training rows, and that any
  resampled rows exist only in training data.
- **FR-044**: The decision threshold or top-K rule MUST be chosen on validation data against
  the operational metric and stated capacity, then applied unchanged to the test set.
- **FR-045**: Validation performance and test performance MUST both be reported so that any
  temporal shift is visible.

#### F. Model candidates and selection [P VI] [G7]

- **FR-050**: The project MUST train and evaluate a dummy baseline (prior-rate or majority
  classifier) and, for ranking comparators, a random-selection baseline and a simple rule
  baseline. `[VERIFY: whether the dataset's rule-flag column is usable as the rule baseline]`
- **FR-051**: The project MUST train and evaluate at least three additional candidates:
  class-weighted logistic regression, a balanced random forest, and a gradient-boosted tree
  model.
- **FR-052**: Each candidate MUST be tuned using training and validation data only, with the
  search space and best configuration saved.
- **FR-053**: All candidates MUST be evaluated on the same test split, with the same metric
  suite and the same K.
- **FR-054**: A model-selection matrix MUST weigh PR-AUC, Recall@K, Precision@K, the
  recall/precision curve, calibration quality, explainability, inference and maintenance risk,
  and investigator workload, and the report MUST state the selection reasoning.
- **FR-055**: Where computationally feasible, comparison tables MUST include variance across
  repeated seeds or bootstrap confidence intervals; if omitted, the omission MUST be stated.
- **FR-056**: The selected model, its fitted preprocessing pipeline, its configuration, its
  metric table, and a model version identifier MUST be saved as artifacts.

#### G. Explainability [P VII] [G8]

- **FR-060**: The project MUST produce global feature-importance explanations for the selected
  model using a Shapley-value method.
- **FR-061**: The project MUST produce local, per-transaction explanations for at least three
  transactions in the top-K list, each with a plain-language caption and the disclaimer.
- **FR-062**: The project MUST produce partial-dependence and/or individual-conditional-
  expectation views for the top features where technically valid, and MUST document and
  justify omission or caveats where they are not, naming the alternative used.
- **FR-063**: Explanations MUST be checked for consistency with the EDA and domain reasoning;
  surprising attributions MUST be discussed in the report.

#### H. Ethical AI and fairness [P VIII] [G9]

- **FR-070**: The project MUST run and record a sensitive-attribute availability check for
  age, gender, ethnicity, nationality, socioeconomic status, and plausible proxies, without
  assuming any are present. `[PROFILE: result]`
- **FR-071**: If valid sensitive-group labels exist, the project MUST compute demographic
  parity, equalized odds, and disparate impact and propose mitigations.
- **FR-072**: If valid sensitive-group labels do not exist, the report MUST state that
  demographic fairness cannot be measured on this dataset, and MUST NOT present any
  substitute as demographic fairness.
- **FR-073**: The project MUST perform an operational error-slice analysis (error rates,
  Recall@K, and calibration by transaction type, amount band, balance band, time band, and
  other non-protected slices) and MUST label it exactly "operational error-slice analysis".
- **FR-074**: The project MUST propose a governance-controlled fairness audit plan for any real
  use, naming required data, metrics, owners, and review cadence.
- **FR-075**: The limitations section MUST address class imbalance handling, leakage risks and
  controls, overfitting evidence, synthetic-label validity, simulator artifacts, and
  non-transferability to real banking data, and MUST state that results cannot establish
  actual fraud/AML effectiveness, fairness, or regulatory suitability.
- **FR-076**: Proposed mitigations (reweighting, threshold adjustment, augmentation,
  post-processing, monitoring) MUST be concrete and feasible for the stated context. Each
  mitigation MUST name the mechanism, the owner role, and the trigger condition that would
  invoke it.

#### I. Human-in-the-loop and output surfaces [P IX] [G10]

- **FR-080**: Every output surface (evaluation tables, top-K lists, notebooks, report, decks,
  optional service) MUST carry the educational disclaimer, defined once and reused verbatim.
- **FR-081**: Outputs MUST be limited to risk score, rank/review-priority recommendation, model
  version, explanation, and disclaimer.
- **FR-082**: The project MUST NOT implement, simulate, or describe any of the prohibited
  actions in "Explicit non-use".
- **FR-083**: The report and business deck MUST describe the human review workflow,
  investigator role, and override capability.
- **FR-084**: A vocabulary check MUST confirm no prohibited determination language is applied
  to model outputs in code, report, or slides.

#### J. Deliverables and communication [P X] [G11]

- **FR-090**: The project MUST produce a final report containing: problem statement, dataset
  overview and data dictionary, EDA + feature engineering report, model comparison and
  selection, explainability, Bias & Fairness Analysis, limitations, and reproducibility
  instructions.
- **FR-091**: The project MUST produce a technical deck of 8–12 slides for peers.
- **FR-092**: The project MUST produce a business deck of 8–12 slides for executives, framing
  ROI as illustrative and presenting risks, strategy, and the human-in-the-loop model.
- **FR-093**: Report and decks MUST be exported in an approved submission format (.pdf, .doc,
  .pptx, or .ppt) and named per the submission instructions.

#### K. Repository, tests, and reproducibility [P III, X] [G3]

- **FR-100**: The public repository MUST contain `src/`, `notebooks/`, `data/` (with README,
  raw and processed gitignored), `models/`, `reports/`, `tests/`, `configs/`, `README.md`,
  `requirements.txt`, `.gitignore`, and a license file.
- **FR-101**: All run parameters (paths, seed, split boundaries, K, feature lists, model
  hyperparameters) MUST be in versioned configuration files; no hardcoded values in notebooks
  or scripts.
- **FR-102**: A single global seed MUST be propagated to every stochastic component.
- **FR-103**: Dependencies MUST be pinned to exact versions and the language runtime version
  declared.
- **FR-104**: Automated tests MUST cover schema validation, data-loading contracts, feature
  functions, the leakage guard, and metric computations, and MUST pass before any deliverable
  is declared complete.
- **FR-105**: The README MUST list ordered commands for environment setup, data fetch,
  pipeline run, tests, and report regeneration, verified on a clean environment.
- **FR-106**: Notebooks MUST be numbered, run top to bottom, and read from configuration.
- **FR-107**: Commit history MUST use descriptive conventional prefixes; no force-pushes to
  the main branch.
- **FR-108**: The README MUST state which optional steps were attempted and which were not.

#### L. Optional work [P XI] [G12]

- **FR-110** (optional Step 8): If deployment is attempted, a local web service MUST load the
  saved pipeline and model artifact and return score, review-priority recommendation, model
  version, and disclaimer, with input validation and a deployment guide and demo recording.
- **FR-111** (optional Step 8): Any containerization, experiment tracking, CI checks,
  monitoring plan, or versioning/rollback plan MUST be documented if present.
- **FR-112** (optional Step 9): If generative AI is used, a usage document MUST record tool and
  model, purpose, representative prompts and outputs, human review performed, and known
  limitations or corrections, and all GenAI-produced factual text MUST be verified against
  pipeline outputs.
- **FR-113**: Optional work MUST live in clearly separated locations and MUST NOT be a
  dependency for the core pipeline, tests, or report.

### Key Entities

- **Transaction**: one synthetic payment event; the unit of analysis. Carries a time step, a
  type, an amount, origin and destination account references, balance fields before and after
  the event, the simulated label, and (if present) a rule-flag column. `[VERIFY: exact field
  set at profiling]`
- **Account reference**: an identifier for origin or destination; used only to derive
  time-ordered aggregates, never as a direct feature.
- **Label (`isFraud`)**: simulated fraud indicator; 1 = simulated fraud, 0 = simulated normal.
- **Engineered feature**: a derived variable with rationale, prediction-time availability
  statement, and data-dictionary entry.
- **Split**: a temporal partition of transactions into training, validation, and test, with
  recorded boundaries.
- **Model candidate**: a named algorithm with a tuned configuration, imbalance strategy,
  fitted preprocessing pipeline, and metric table on the common test split.
- **Risk score**: the selected model's probability-like output for a transaction.
- **Review queue**: for a review period, the transactions ranked by risk score with a
  deterministic tie-break; the top-K subset is the daily review list.
- **Review capacity (K)**: an illustrative configured integer.
- **Operating point**: the validation-chosen threshold or top-K rule applied to test.
- **Explanation**: global importance summary or per-transaction attribution with caption.
- **Operational slice**: a non-protected partition of transactions (type, amount band, balance
  band, time band) used for error-slice analysis.
- **Sensitive-attribute availability record**: per candidate attribute, whether a valid label
  exists and the evidence.
- **Artifact**: saved model, fitted pipeline, configuration, and metric table under a model
  version identifier.
- **Disclaimer**: the single educational-use statement reused on every output surface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the held-out temporal test set, the selected model's Recall@K exceeds both
  random selection and the dummy baseline at the same K, and its PR-AUC exceeds the class
  prevalence (the no-skill PR-AUC). Achieved values: `[MEASURED: at evaluation]`.
- **SC-002**: The selected model's Recall@K is reported alongside the rule baseline's Recall@K
  at the same K, and the comparison is discussed whether or not the model wins.
  `[MEASURED: at evaluation]`
- **SC-003**: A peer following only README commands on a clean environment reproduces every
  metric table and figure cited in the report and decks, with identical values given the fixed
  seed (or within a stated tolerance).
- **SC-004**: 100% of automated tests pass, including the leakage guard and schema tests.
- **SC-005**: Zero data files, credentials, or secrets are present in the repository history at
  submission.
- **SC-006**: The dummy baseline plus at least three candidate models are evaluated on the same
  split with the same metric suite and K, and a selection matrix is present.
- **SC-007**: At least one feature-selection method and PCA are applied on training data only
  and documented with before/after evidence.
- **SC-008**: Global and at least three local explanations exist for the selected model, plus
  PDP/ICE views or documented alternatives for the top features.
- **SC-009**: The Bias & Fairness Analysis contains the sensitive-attribute availability
  record, either demographic metrics or an explicit statement that they cannot be computed, an
  operational error-slice analysis labeled as such, limitations, and a governance audit plan.
- **SC-010**: 100% of output surfaces carry the disclaimer, and a vocabulary check finds zero
  prohibited determination terms applied to model outputs.
- **SC-011**: Two decks exist, each with 8–12 slides, and the final report contains every
  required section.
- **SC-012**: The repository matches the required structure, and the README states the status
  of optional Steps 8 and 9.
- **SC-013**: A self-assessment against every rubric criterion's "Outstanding/Exemplary"
  descriptors is present with each gap closed or acknowledged.

## Assumptions

- **Dataset**: PaySim from the recorded Kaggle source is the sole dataset; no additional or
  real data is introduced. Its license permits educational, non-commercial use, pending
  verification at download time.
- **Time index**: PaySim's `step` field is a usable time ordering for temporal splitting and
  causal aggregates. If profiling shows otherwise, FR-041 applies.
- **Rule-flag column**: the dataset's rule-based flag, if present, is excluded from features
  and used only as a rule baseline. If absent, a simple documented amount-based rule is used
  instead.
- **Sensitive attributes**: expected to be absent from PaySim; the project proceeds on the
  operational-slice path unless profiling shows otherwise.
- **Review capacity K**: an illustrative integer chosen after profiling transactions per step;
  the project may report a small set of K values to show sensitivity, with one designated
  primary.
- **Compute**: if the full dataset is too large for repeated tuning on the available hardware,
  a seeded, documented subsample may be used for hyperparameter search, while final training
  and test evaluation use the full split. Any subsampling is recorded in configuration and the
  report.
- **Report format**: authored in Markdown and exported to PDF for submission; decks authored
  in any tool and exported to PDF or PPTX.
- **Optional steps**: Steps 8 and 9 are pursued only after Steps 1–7 satisfy their quality
  gates. Local deployment, if attempted, targets a local web service as recorded in project
  decisions.
- **Financial impact**: no currency values or real-world savings are estimated anywhere;
  business value is expressed as illustrative counts and relative improvements.
- **Audience**: graders assess against the rubric's top band only; lower bands are out of
  scope.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R1 | Temporal split leaves too few or no positives in validation/test | Medium | High | Profile positives per step before fixing boundaries; fallback per FR-041 |
| R2 | Post-transaction balance fields leak the label | High | High | Prediction-time availability review per feature; leakage tests; ablation with suspect fields removed |
| R3 | Simulator artifacts make the task unrealistically easy, inflating metrics | Medium | High | Report artifacts explicitly; compare against rule baseline; state non-transferability |
| R4 | Compute cost of full dataset with tuning and Shapley explanations | Medium | Medium | Seeded subsampling for tuning and explanation sampling, documented |
| R5 | Overclaiming fairness from operational slices | Low | High | FR-072/FR-073 labeling rules; vocabulary check; reviewer sign-off |
| R6 | Determination language slips into decks or code | Medium | High | Single disclaimer constant; vocabulary check in tests |
| R7 | License terms change or cannot be verified | Low | High | Record license at download; do not redistribute data; stop if unverifiable |
| R8 | Non-determinism in libraries breaks exact reproducibility | Medium | Medium | Fix seeds and thread counts where possible; state tolerance |
| R9 | Optional work consumes time needed for core deliverables | Medium | Medium | Gate optional work behind G1–G11 completion |
| R10 | Committing data or secrets by accident | Low | High | `.gitignore` for data; secret scan pre-merge |

## Validation Tasks & Placeholders

Every placeholder in this document MUST be resolved by one of the following tasks before the
corresponding requirement is marked complete. Results are recorded in the data quality report,
configuration, or evaluation outputs, never asserted in advance.

| ID | Placeholder | Resolving task | Output location |
|----|-------------|----------------|-----------------|
| V1 | Dataset license text | Inspect the Kaggle dataset page at download time; record text and date | `data/README.md` |
| V2 | Exact column names and types | First-load inspection; encode as schema check | Schema config and test |
| V3 | Row count, nulls, duplicates, outliers, invalid values | Data quality profiling | Data quality report |
| V4 | Class imbalance ratio and positives by transaction type and by time step | Profiling | Data quality report, EDA |
| V5 | Which balance fields are post-transaction and whether balance arithmetic is consistent per type | Profiling and feature review | Data dictionary, feature rationale |
| V6 | Presence and firing rate of the rule-flag column | Profiling | Data quality report; rule-baseline definition |
| V7 | Sensitive-attribute and proxy availability | Availability check | Bias & Fairness Analysis |
| V8 | Transactions per time step; choice of K | Profiling | Configuration; framing section |
| V9 | Temporal split boundaries with sufficient positives | Profiling | Configuration |
| V10 | Which candidate features are computable and informative | Feature engineering and selection | Data dictionary; EDA + FE report |
| V11 | All metric values, KPI counts, selection matrix entries | Evaluation | Model comparison outputs |
| V12 | Validity of PDP/ICE for top features | Explainability analysis | Explainability section |
| V13 | Reproducibility tolerance, if any | Repeated-run check | README |

## Definition of Done

The feature is DONE when all of the following hold:

1. All functional requirements FR-001 through FR-108 are satisfied with evidence linked from
   the README or final report; FR-110 through FR-113 are satisfied for any optional step that
   was attempted, and the README states which were not.
2. All success criteria SC-001 through SC-013 are met, with measured values recorded in place
   of `[MEASURED]` placeholders and every `[PROFILE]` / `[VERIFY]` placeholder resolved via
   the validation tasks.
3. Constitution gates G1–G12 are satisfied with evidence, and the plan's Constitution Check
   records no unjustified violations.
4. The pipeline runs end to end from a clean clone using only README commands and reproduces
   every reported figure and metric.
5. All automated tests pass.
6. The public repository has the required structure and no committed data or secrets.
7. The final report, technical deck, and business deck are exported in an approved format and
   named per the submission instructions.
8. No deliverable claims real-world AML effectiveness, real-data applicability, or demographic
   fairness beyond what the evidence supports.

## Out of Scope

- Real customer or bank data of any kind.
- Any automated action on transactions or accounts.
- Customer- or entity-level risk scoring, network/graph analysis across accounts as a
  determination tool, or regulatory reporting.
- Production deployment, cloud hosting, or integration with any bank system. Cloud deployment
  is optional under the assignment and is not planned.
- Monetary ROI estimation.
- Demographic fairness measurement on PaySim unless profiling unexpectedly reveals valid
  sensitive-group labels.
