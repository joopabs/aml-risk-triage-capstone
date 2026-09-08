# Feature Specification: Batch Transaction-Risk Triage UI

**Feature Branch**: `002-batch-triage-ui`

**Created**: 2026-09-08

**Status**: Draft

**Input**: User description: "Create a feature specification for 'Batch Transaction-Risk Triage
UI': an interactive web front end on top of the existing scoring service that lets an investigator
upload a CSV file or paste multiple transaction entries, scores them with the released model bundle
and its frozen operating point, and displays a ranked review queue." (Full input retained in the
invoking command; source documents: `CAPSTONE_BRIEF.md`, `PROJECT_DECISIONS.md`,
`.specify/memory/constitution.md`, `specs/001-aml-risk-triage/spec.md`.)

**Upstream dependency**: `specs/001-aml-risk-triage/` (complete, all 101 tasks done). This feature
consumes its released model bundle (`models/LATEST`), frozen operating point, request/response
contract (`contracts/scoring-api.yaml`), and single-transaction scoring service. Nothing in the
upstream feature is modified, retrained, or re-evaluated. The test split is never touched.

**Governing constitution**: v1.0.0. Requirements map to principles (I–XI) and gates (G1–G12)
inline as `[P#]` / `[G#]`.

**Placeholder convention**: as upstream. `[MEASURED: …]` marks values that must come from running
the built feature; `[VERIFY: …]` marks facts to confirm against the repository. No performance
number, threshold, K, or model metric in this document is asserted as fact; the operating point
values are referenced by name and read from `configs/operating_point.yaml` at run time.

---

## Clarifications

### Session 2026-09-08

- Q: When a batch is ranked, which rows should be marked `high`? → A: Rank ≤ K **and** raw score
  at or above the frozen threshold; remaining rows `medium` if above the threshold, else `low`
  (Option B). A batch smaller than K therefore has at most as many `high` rows as it has
  above-threshold rows; on a full review period the result equals the pipeline's `queue` report.
- Q: When some rows fail validation, should valid rows still be scored or the whole batch be
  refused? → A: Skip and report (Option A): valid rows are scored; each invalid row is listed with
  row number, field, and reason, and the skipped list is exportable. Whole-file refusal applies only
  to structural problems: unknown columns, empty file, or a file over the batch size limit.
- Q: What should the default batch size limit be? → A: 5,000 rows (Option B), a configuration
  value shown on the upload screen; the scoring time at that limit is measured (V1) and the limit
  may be raised in configuration if the measurement allows.

---

## Business Context & Scope

### Problem statement

The upstream capstone delivers a ranked daily review queue as a static report and a service that
scores one transaction at a time. Investigators triage in batches: a day's worth of transactions,
an export from a case system, or a handful of entries typed in during a review. This feature adds
an interactive local web front end in which an investigator supplies many synthetic PaySim-style
transactions at once, receives a ranked queue with a risk score, a review-priority recommendation,
and the main contributing factors for each row, and exports that queue. It is an educational
prototype on synthetic data, exactly as the upstream feature.

### Users

- **Investigator / reviewer** (primary): loads a batch, reads the ranked queue, opens a row's
  explanation, exports the queue to continue review elsewhere, and decides what to do. The human
  decides; the tool orders the work.
- **Reviewer of the capstone** (secondary): runs the UI locally from documented commands to see the
  released model in an interactive setting.

### Intended use

Ordering a batch of synthetic transactions for human review by the released model's risk score and
the frozen operating point. Every screen states that the output is a review priority, not a
determination.

### Explicit non-use [P IX]

The UI MUST NOT implement, simulate, offer, or describe as available: automatic transaction
blocking, account closure, customer risk rating, suspicious-activity or regulatory filing, or any
actual AML determination. No control on any screen performs or records a decision about a
transaction; there is no "approve", "block", "hold", "escalate to filing" or equivalent action.
Uploaded data describes synthetic PaySim transactions and MUST NOT be described as real SME,
corporate, or Philippine banking data [P II].

### Relationship to the Step 8 deployment of record [P XI]

The assignment allows local deployment via Flask, FastAPI, or Dash. The existing scoring service
remains the Step 8 deployment of record. This UI is an additional local component that calls that
service; it is optional, separated in the repository, and not a dependency of the core pipeline,
report, or the existing service. The UI framework is chosen in the plan and justified against the
constitution's stack rule; if it is not one of the three frameworks named in the brief, the README
and deployment guide MUST say so and name the service as the deployment of record.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a CSV and see a ranked review queue (Priority: P1)

An investigator uploads a CSV file whose columns match the single-transaction request schema. The
UI validates every row, scores the valid rows with the released bundle, ranks them within the
batch, assigns a review priority per the frozen operating point, and shows a sortable table:
rank, risk score, review priority, transaction type, amount, and the model version, with the
disclaimer visible.

**Why this priority**: This is the feature. Without it nothing else has value.

**Independent Test**: Upload a small synthetic CSV (for example the rows behind the existing
`reports/review_queue_period_0.md`), confirm the table shows one row per valid input in rank
order, that the top rows carry `high`, that the disclaimer is on screen, and that the same rows
scored by the existing single-transaction service produce identical risk scores.

**Acceptance Scenarios**:

1. **Given** a CSV with N valid rows, **When** it is uploaded, **Then** the queue shows N rows
   ordered by rank 1..N, each with risk score, review priority, model version, and the disclaimer
   is visible without scrolling past the table.
2. **Given** a batch with more than K rows whose top K all score at or above the frozen
   threshold, **When** scored, **Then** exactly K rows are `high` (FR-020) and the rest carry
   `medium` or `low` from the frozen threshold; **Given** a batch whose rows all score below the
   threshold, **When** scored, **Then** no row is `high`.
3. **Given** the same rows submitted one by one to the existing single-transaction service,
   **When** the batch is scored, **Then** every row's risk score is identical to the single
   response for that row.
4. **Given** the CSV includes columns not in the schema, **When** uploaded, **Then** the UI
   refuses the file and names the unexpected columns; no row is scored.

---

### User Story 2 - Enter several transactions by hand (Priority: P2)

An investigator without a file types or pastes several transactions into an editable grid (one
row per transaction, the same columns as the CSV) and scores them the same way.

**Why this priority**: Covers ad-hoc review and demos where no file exists; reuses the P1 path.

**Independent Test**: Enter three rows manually, including one that empties the origin account,
score them, and confirm the table shows three ranked rows with the emptied-account row first.

**Acceptance Scenarios**:

1. **Given** the manual grid, **When** rows are added and "Score batch" is pressed, **Then** the
   result is identical to uploading the same rows as CSV.
2. **Given** a manual row with a missing required value, **When** scored, **Then** the row is
   reported as invalid with its row number and the missing field, and the remaining rows are
   scored (see FR-012 for the skip-and-report rule).
3. **Given** a single row, **When** scored, **Then** its review priority follows the score-only
   bands used by the single-transaction service (no ranking exists for one row).

---

### User Story 3 - Understand why a row is where it is (Priority: P3)

For any row in the queue the investigator opens an explanation showing the top contributing
factors in plain language with their direction, the same content the single-transaction service
returns, plus the model version and the disclaimer.

**Why this priority**: Explainability is a constitution requirement for anything shown to a
business audience [P VII]; investigators must be able to interrogate the order.

**Independent Test**: Select the top-ranked row and a low-ranked row; confirm each shows up to
five factors with plain-language sentences and that the factors match the single-transaction
service's output for that row.

**Acceptance Scenarios**:

1. **Given** a scored queue, **When** a row is selected, **Then** its factors, their direction,
   and plain-language sentences are shown with the disclaimer.
2. **Given** the explanation panel, **When** read, **Then** no sentence uses prohibited
   determination vocabulary (FR-041).

---

### User Story 4 - Export the ranked queue (Priority: P4)

The investigator downloads the ranked queue as a CSV that contains the input columns, rank, risk
score, review priority, model version, and the disclaimer text, so review can continue outside
the tool.

**Why this priority**: Makes the tool useful in a workflow; also the only artifact that leaves the
session, so it must carry the disclaimer.

**Independent Test**: Export after scoring; open the file; confirm row count, column set, rank
order, and that the disclaimer is present in the file.

**Acceptance Scenarios**:

1. **Given** a scored queue, **When** "Export" is pressed, **Then** a CSV downloads with one row
   per scored transaction in rank order and the disclaimer included (as a header comment line or a
   column, decided in the plan and applied consistently).
2. **Given** invalid rows were skipped, **When** exported, **Then** the export lists the skipped
   rows with their reasons in a separate section or file so nothing is silently dropped.

---

### User Story 5 - Clear feedback on bad input (Priority: P5)

Rows that fail validation (missing field, non-numeric value, negative amount, unknown transaction
type, extra field) are reported individually with the row number, the field, and the reason. Files
over the batch size limit, empty files, and files with the wrong columns are refused with a clear
message.

**Why this priority**: Correct validation is what keeps the scoring honest; it is inseparable
from P1 but independently testable.

**Independent Test**: Upload a CSV with one row per failure type; confirm each is listed with row
number, field, and reason, and that the valid rows still score.

**Acceptance Scenarios**:

1. **Given** a file with invalid rows, **When** uploaded, **Then** each invalid row appears in a
   validation report with row number, field, and reason, and the valid rows are scored.
2. **Given** a file above the batch size limit, **When** uploaded, **Then** it is refused with a
   message stating the limit; nothing is scored.
3. **Given** an empty file or a file with only a header, **When** uploaded, **Then** the UI says
   there is nothing to score.

---

### User Story 6 - Run it locally from documented commands (Priority: P6)

A reviewer installs the UI's pinned dependencies, starts the service and the UI with documented
make targets, loads the bundled example file, and sees the queue. The deployment guide, README,
GenAI usage record, and MLOps plan describe the UI and its boundaries.

**Why this priority**: Reproducibility and transparency of optional work [P III, P XI].

**Independent Test**: Follow the documented commands on a clean environment; the UI starts, the
example file scores, and the documentation states which framework is the deployment of record.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the documented setup and run commands are executed,
   **Then** the UI is reachable locally and the example batch scores.
2. **Given** the repository, **When** the UI code and its requirements file are removed, **Then**
   the core pipeline, tests, report, and the existing service still run.

---

### Edge Cases

- Batch smaller than K: at most the above-threshold rows are `high` (FR-020); the UI states that
  the batch is below review capacity K (as the `queue` report states a shortfall).
- Exactly one valid row: score-only bands apply; the UI says no ranking was performed.
- Ties in raw score: deterministic tie-break (same rule as the pipeline's ranking) so re-scoring
  the same batch gives the same order.
- Duplicate rows in the batch: scored and ranked independently; the UI shows a duplicate count.
- Optional aggregate columns absent: defaults from the request schema apply (documented on screen).
- Columns present but reordered or with surrounding whitespace in headers: accepted after
  normalisation; unknown columns are refused.
- Unknown transaction type: the row is invalid (the service rejects it); it is reported, not
  scored.
- Non-UTF-8 or non-CSV file: refused with a message.
- Scoring service unavailable: the UI shows a clear message and does not fall back to a local
  model copy (single scoring path, FR-021).
- Very large valid batch within the limit: scoring completes; explanation is computed on demand
  per selected row rather than for every row up front (plan decides; FR-032).
- Browser refresh: the batch is gone; nothing was persisted (FR-050).

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. Inputs [P V]

- **FR-001**: The UI MUST accept a CSV file whose columns are exactly the fields of the
  single-transaction request schema (`contracts/scoring-api.yaml`, `TransactionRequest`):
  required `step`, `type`, `amount`, `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`,
  `newbalanceDest`; optional `orig_prior_txn_count`, `orig_prior_amount_sum`,
  `dest_prior_txn_count`, `dest_prior_amount_sum`, `dest_is_merchant` with the schema defaults.
- **FR-002**: The UI MUST accept manual entry of one or more rows with the same columns, and MUST
  treat manual rows and CSV rows identically from validation onward.
- **FR-003**: The UI MUST refuse files with unknown columns (naming them), files over the batch
  size limit (stating the limit), and empty files, without scoring any row.
- **FR-004**: The batch size limit MUST be a configuration value, default 5,000 rows (clarified
  2026-09-08), shown on the upload screen; files with more rows are refused before any scoring.
  `[MEASURED: scoring time at the limit on the development machine, recorded in the deployment
  guide]`; the default MAY be raised in configuration if the measurement shows headroom.
- **FR-005**: The UI MUST ship a small synthetic example CSV (rows drawn from the existing
  synthetic examples, never from raw PaySim data files) so a reviewer can try it without preparing
  data. The example MUST be labelled synthetic.

#### B. Validation [P V]

- **FR-010**: Every row MUST be validated against the request schema before scoring: required
  fields present, numeric fields numeric, `step` ≥ 1, `amount` ≥ 0, aggregate counts and sums
  ≥ 0, `type` one of the types known to the released bundle, `dest_is_merchant` boolean.
- **FR-011**: Validation failures MUST be reported per row with the input row number, the field,
  and a plain reason.
- **FR-012**: Invalid rows MUST be skipped and reported; valid rows in the same batch MUST still be
  scored. The UI MUST show counts of scored and skipped rows. Whole-file refusal (nothing scored)
  applies only to structural problems: unknown columns, empty file, or a file over the batch size
  limit (FR-003). There is no mode that refuses a batch because of row-level failures.
- **FR-013**: Header normalisation (whitespace, case) MAY be applied; any other transformation of
  input values is prohibited.

#### C. Scoring and ranking [P IV, P VI, P IX] [G4, G7]

- **FR-020**: For a batch of two or more valid rows, review priority MUST be assigned by the batch
  ranking rule: rows are ranked by raw model score with the pipeline's deterministic tie-break;
  a row is `high` when its rank ≤ K **and** its raw score is at or above the frozen threshold,
  where K is `primary_k` and the threshold is `threshold` from the frozen operating point
  (`configs/operating_point.yaml`, read at run time, never hard-coded); remaining rows are
  `medium` if their raw score is at or above the threshold and `low` otherwise. Consequences:
  a batch smaller than K has at most as many `high` rows as it has above-threshold rows; a batch
  of routine transactions yields no `high` rows; on a full review period of the upstream data the
  `high` set equals the pipeline's `queue` report (SC-003). The rule MUST be stated on screen in
  plain words next to the queue.
- **FR-021**: All scoring MUST go through one scoring path shared with the existing
  single-transaction service (same fitted feature pipeline, same estimator, same calibrator for
  the displayed probability, same operating point). The UI MUST NOT load or contain a second copy
  of the model.
- **FR-022**: For a single valid row the score-only bands of the single-transaction service MUST
  apply, and the UI MUST state that no ranking was performed.
- **FR-023**: The displayed risk score MUST be the same quantity the single-transaction service
  returns (`risk_score`); ranking MUST use the raw score, as in the pipeline.
- **FR-024**: The released bundle MUST be used as is: no retraining, no re-fitting, no access to
  any split of the dataset, no change to the operating point. `[VERIFY: no code path in this
  feature reads `data/`]`.
- **FR-025**: Scores and ranks for a given batch MUST be deterministic: re-submitting the same
  rows yields identical output.

#### D. Output and explanation [P VII, P IX] [G8, G10]

- **FR-030**: The queue MUST show, per scored row: rank, risk score, review priority, transaction
  type, amount, and model version; it MUST be sortable by these columns without changing the
  stored rank.
- **FR-031**: The queue MUST NOT show any field named or functioning as a decision (see
  `PROHIBITED_OUTPUT_FIELDS` upstream: allow, block, decision, hold, sar, filing, and
  equivalents), and MUST NOT offer any action on a transaction beyond viewing and exporting.
- **FR-032**: For any selected row the UI MUST show the top contributing factors (up to five) with
  direction and the plain-language sentence produced by the shared scoring path. Explanations MAY
  be computed on demand rather than for every row.
- **FR-033**: Every screen and panel that shows a score, priority, or explanation MUST display the
  educational disclaimer verbatim from the single shared definition [G10].
- **FR-034**: The UI MUST display the model version and the operating point values in use (K,
  threshold) as read from the released bundle and configuration, labelled as the frozen operating
  point.

#### E. Export [P IX, P X]

- **FR-040**: The UI MUST export the scored queue as CSV in rank order with the input columns,
  rank, risk score, review priority, and model version, and MUST include the disclaimer text in
  the file.
- **FR-041**: Exports and all UI text MUST pass the upstream vocabulary check (FR-084 upstream):
  no "fraudulent", "launderer", "guilty", "confirmed", "suspicious activity report" or equivalent
  applied to outputs; positives are "simulated fraud" where labels are discussed at all.
- **FR-042**: Skipped rows and their reasons MUST be exportable alongside the queue so no input is
  silently lost.

#### F. Privacy and data handling [P II]

- **FR-050**: Uploaded and typed data MUST be processed in memory only. The UI and the batch
  scoring path MUST NOT write inputs, scores, or exports to disk, logs, caches, or telemetry.
  Framework-level usage statistics or telemetry MUST be disabled.
- **FR-051**: The accepted columns are exactly the request schema; no account identifiers, names,
  or free-text fields are accepted (the upstream schema has none). Any extra column is refused,
  not dropped.
- **FR-052**: The UI MUST state on the upload screen that data is processed in memory and not
  stored, and that the tool is for synthetic PaySim-style transactions.

#### G. Deployment, separation, and reproducibility [P III, P XI] [G3, G12]

- **FR-060**: The UI MUST run locally from documented make targets, with its dependencies pinned in
  a separate requirements file so the core pipeline's environment is unchanged.
- **FR-061**: The UI MUST be a separate, removable component: with the UI code and its requirements
  removed, the core pipeline, tests, report, and the existing service run unchanged.
- **FR-062**: The existing scoring service MUST remain the Step 8 deployment of record; the README
  and deployment guide MUST state this and name the UI framework and why it was chosen.
- **FR-063**: If the batch scoring path is exposed by the service, its contract MUST be added to the
  upstream contract directory's successor for this feature (`specs/002-batch-triage-ui/contracts/`)
  and MUST keep `additionalProperties: false` on responses so no decision field can appear.
- **FR-064**: The service's health information (model version, disclaimer) MUST be shown in the UI
  so the reviewer can see which bundle is loaded.

#### H. Tests [P III] [G3, G10]

- **FR-070**: Automated tests MUST cover: CSV parsing and column checks; per-row validation and
  skip-and-report; the batch ranking rule including ties, batches smaller than K, and the single-row
  case; equality of batch scores with single-transaction scores on the same rows; export contents
  including the disclaimer; absence of prohibited fields and vocabulary in UI text and exports; no
  file writes during scoring.
- **FR-071**: Tests MUST use the existing small synthetic API test bundle; no test reads real data.
- **FR-072**: The UI tests MUST run in CI in an optional job, mirroring the existing optional API
  job, and the core test suite MUST remain green without the UI dependencies installed.

#### I. Documentation [P X, P XI] [G11, G12]

- **FR-080**: README: status line for this optional component, run commands, and the framework
  statement (FR-062).
- **FR-081**: Deployment guide: UI section with setup, run, example batch, the batch ranking rule
  in plain words, the batch size limit, the privacy statement, limits, and a demo capture
  (GIF or screencast) of a real batch being scored.
- **FR-082**: GenAI usage record: the uses of generative AI in building this feature, with
  representative prompts, human review, and errors found, in the same format as the existing
  record.
- **FR-083**: MLOps plan: how the UI is versioned with the bundle, how a bundle rollback affects
  it, and what monitoring a real deployment would add.
- **FR-084**: Final report and decks are NOT modified by this feature unless the user asks; if they
  are, only the optional-work status text changes.

### Key Entities

- **Batch**: one submission (file or manual grid); attributes: source (upload/manual), row count,
  scored count, skipped count, submitted-at (session only), model version used, operating point in
  use.
- **Transaction row**: one input row with the request-schema fields and its input row number.
- **Validation issue**: input row number, field, reason.
- **Scored row**: transaction row plus raw score (internal), risk score (displayed), rank, review
  priority, model version.
- **Explanation**: for one scored row, up to five factors with contribution, direction, and
  plain-language sentence.
- **Queue export**: the scored rows in rank order plus the disclaimer, and the validation issues.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a batch of valid rows, 100% of rows appear in the queue exactly once, in rank
  order, each with a risk score, review priority, and model version.
- **SC-002**: For every row in a test batch, the batch risk score equals the single-transaction
  service's risk score for that row (0 differences).
- **SC-003**: On the rows of one review period from the existing `queue` report, the UI's top-K
  set and their priorities match the report (0 differences).
- **SC-004**: 100% of screens and exports that show a score or priority contain the disclaimer
  verbatim; the vocabulary check passes on all UI text and export content.
- **SC-005**: A batch with one row of each validation failure type reports every failing row with
  row number, field, and reason, and scores all valid rows.
- **SC-006**: Scoring a batch at the configured size limit completes and displays within
  `[MEASURED: seconds on the development machine]`, recorded in the deployment guide; the UI
  remains usable while scoring runs.
- **SC-007**: No file is created or modified under the repository or the user's home directory by
  uploading, scoring, or exporting (checked by a test that snapshots the filesystem).
- **SC-008**: With the UI component removed, the core pipeline tests, `make smoke`, the report
  build, and the existing service's tests pass unchanged.
- **SC-009**: A reviewer can install and start the UI and score the bundled example with only the
  documented commands on a clean environment.

---

## Assumptions

- The released bundle `models/LATEST` and `configs/operating_point.yaml` are the only model
  artifacts used; they are not modified.
- The single-transaction service's request schema is the authoritative column set; the UI does not
  accept identifiers because the upstream feature removed them deliberately (FR-033 upstream).
- K and the threshold are read from the frozen operating point at run time; the values are not
  written into UI code or documentation as facts.
- Default batch size limit 5,000 rows (clarified), adjustable in configuration; chosen as a
  realistic slice of one review period that keeps scoring and on-demand explanation interactive on
  a laptop. `[MEASURED]` in the plan's validation (V1).
- The UI calls the local scoring service over the loopback interface only; no authentication is
  added (local demo scope, consistent with the existing service's limits).
- Explanations are produced by the same explainer the service uses; if the explainer is
  unavailable, the UI shows "no explanation available" rather than a substitute.
- The UI framework is decided in the plan (research task); the spec is framework-agnostic.

## Dependencies

- Upstream feature `001-aml-risk-triage` complete and merged (released bundle, operating point,
  service, contracts, tests, docs).
- The existing optional API job in CI and its synthetic test bundle fixture.
- Pinned Python 3.11 environment and `uv` for compiling the UI requirements file.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Batch `high` band misread as a determination | Medium | High | Disclaimer on every screen, no action controls, vocabulary check, FR-020 rule explained on screen |
| R2 | Framework telemetry or caching writes user data | Medium | High | FR-050; telemetry disabled in configuration; filesystem-snapshot test (SC-007) |
| R3 | UI drifts from the service (second model copy, different bands) | Medium | High | FR-021 single scoring path; SC-002/SC-003 equality tests |
| R4 | Framework outside the brief's list weakens the Step 8 claim | Medium | Medium | Existing service stays deployment of record; stated in README and guide (FR-062) |
| R5 | Large batches make the UI unresponsive | Medium | Medium | Batch size limit (FR-004); explanation on demand (FR-032); measured in SC-006 |
| R6 | Optional work becomes a dependency of the core | Low | High | Separate requirements file, optional CI job, removal test (SC-008) |

## Validation Tasks & Placeholders

| ID | Placeholder | Resolved by |
|---|---|---|
| V1 | `[MEASURED]` scoring time at the batch size limit (FR-004, SC-006) | Timed run recorded in the deployment guide |
| V2 | `[VERIFY]` no code path in this feature reads `data/` (FR-024) | Grep and a test asserting no data-directory access |
| V3 | FR-020 `high` rule (resolved 2026-09-08: rank ≤ K and score ≥ threshold) | SC-003 comparison against the existing queue report |
| V4 | Framework choice and its justification (FR-062) | Plan research entry; README and deployment guide text |

## Constitution Check

| Principle / gate | How this feature complies |
|---|---|
| P II, G2 | No identifiers accepted; in-memory processing; synthetic-data notice on screen; no data files added; secret scan unchanged |
| P III, G3 | Pinned separate requirements; documented make targets; deterministic output; tests in CI |
| P IV, G4 | No fitting of any kind; released pipeline reused; test split never read |
| P VI, G7 | Released model only; operating point read from configuration |
| P VII, G8 | Per-row factors in plain language, same as the service |
| P IX, G10 | Disclaimer everywhere; no decision fields or actions; vocabulary check on UI text and exports |
| P X, G11 | README, deployment guide, docs updated; report and decks untouched unless requested |
| P XI, G12 | Optional, separated, removable; deployment of record stated; GenAI record updated |

## Definition of Done

1. User stories P1–P6 pass their independent tests; SC-001 to SC-009 observed and recorded.
2. Tests for FR-070 pass locally and in the optional CI job; the core suite passes without UI
   dependencies.
3. Deployment guide, README, GenAI usage record, and MLOps plan updated; demo capture committed.
4. Vocabulary check and secret scan pass; no data, exports, or uploads committed.
5. PR merged to `main` with linear history; branch realigned.

## Out of Scope

- Authentication, multi-user sessions, persistence of batches or review outcomes.
- Cloud deployment.
- Any change to features, model, operating point, split, or the upstream reports and decks.
- Recording investigator decisions or feedback (would be a decision system, see Explicit non-use).
