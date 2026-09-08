# Tasks: Batch Transaction-Risk Triage UI

**Input**: Design documents from `specs/002-batch-triage-ui/` (spec.md, plan.md, research.md,
data-model.md, contracts/, quickstart.md). Constitution v1.0.0 governs.

**Prerequisites**: upstream feature `001-aml-risk-triage` complete on `main`; `models/LATEST`
released; `pipeline.joblib` present locally (`make pipeline` regenerates it if missing).

**Tests**: requested by the spec (FR-070..FR-072). Test tasks come first in each phase and MUST fail
before the implementation task that makes them pass. No test reads real data; `tests/api` and
`tests/ui` use the synthetic `api_bundle` fixture and `importorskip` their optional dependency.

**Organization**: Phase 1 setup, Phase 2 foundational (the batch endpoint every story needs), then
one phase per user story in priority order, then polish. Each task lists: milestone (M1 endpoint,
M2 UI, M3 packaging/docs), type (code / tests / config / docs / verification), dependencies, files,
acceptance, verification.

**Rules carried from the constitution and upstream**: no retraining, no dataset access, no second
model copy, nothing persisted, disclaimer verbatim from `aml_triage.constants.DISCLAIMER`, no
decision fields or actions, triage vocabulary only, green suite before every commit, commits on
`002-batch-triage-ui`, PR merged with rebase, branch realigned afterwards. Do not modify
`specs/001-aml-risk-triage/**`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1..US6 from spec.md; setup, foundational, and polish tasks carry no story label

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pinned UI environment, configuration, make targets, package skeleton, guard tests.

- [ ] T001 Create `requirements-ui.in` (`-c requirements.txt`, `-c requirements-api.txt`, `streamlit`, `requests`) and compile `requirements-ui.txt` with `uv pip compile requirements-ui.in -o requirements-ui.txt`; install into `.venv` and verify the pinned Streamlit imports next to pandas 3.0.5 (plan V5, research R-07)
  - Milestone M2 / Type: config / Depends: none
  - Files: `requirements-ui.in`, `requirements-ui.txt`
  - Accept: compile succeeds without changing any pin in `requirements.txt` or `requirements-api.txt`; `python -c "import streamlit, pandas; print(streamlit.__version__)"` works in `.venv`; if the newest Streamlit is incompatible, pin the newest compatible release and record why in `research.md` R-07
  - Verify: `uv pip sync --python .venv/bin/python requirements.txt requirements-dev.txt requirements-api.txt requirements-ui.txt && .venv/bin/python -c "import streamlit"`
- [ ] T002 [P] Add `.streamlit/config.toml` (`browser.gatherUsageStats=false`, `server.headless=true`, `server.address="127.0.0.1"`, `server.maxUploadSize` sized for the row limit, `logger.level="error"`) and `configs/ui.yaml` (`api_url: http://127.0.0.1:8000`, `explain_default: high`, `request_timeout_seconds`) per research R-06
  - Milestone M2 / Type: config / Depends: none
  - Files: `.streamlit/config.toml`, `configs/ui.yaml`
  - Accept: both files parse; no user-data setting enables caching or telemetry; the batch limit is NOT in `configs/ui.yaml` (it comes from the service)
  - Verify: `.venv/bin/python -c "import tomllib,yaml;tomllib.load(open('.streamlit/config.toml','rb'));yaml.safe_load(open('configs/ui.yaml'))"`
- [ ] T003 [P] Add make targets `setup-ui` (sync all four requirements files), `ui` (`$(PY) -m streamlit run src/aml_triage/ui/app.py`), `ui-test` (`$(PY) -m pytest tests/ui tests/api -q`) to `Makefile` and list them in `make help`
  - Milestone M3 / Type: config / Depends: none
  - Files: `Makefile`
  - Accept: `make -n setup-ui ui ui-test` print the expected commands; `.PHONY` updated
  - Verify: `make -n setup-ui ui ui-test`
- [ ] T004 [P] Create the UI package skeleton: `src/aml_triage/ui/__init__.py` (docstring: optional component, no core import may depend on it) and `src/aml_triage/ui/texts.py` with every fixed string from `contracts/ui-contract.md` (TITLE, PURPOSE, PRIVACY_NOTE, SYNTHETIC_NOTE, RULE_TEXT, BELOW_CAPACITY, SINGLE_ROW, SERVICE_DOWN, UNKNOWN_COLUMNS, EMPTY_FILE, OVER_LIMIT, UNREADABLE) and `DISCLAIMER` imported from `aml_triage.constants`
  - Milestone M2 / Type: code / Depends: none
  - Files: `src/aml_triage/ui/__init__.py`, `src/aml_triage/ui/texts.py`
  - Accept: module imports without Streamlit installed (texts only); disclaimer is not retyped
  - Verify: `.venv/bin/python -c "from aml_triage.ui import texts; assert texts.DISCLAIMER"`
- [ ] T005 [P] Extend guard tests: `tests/test_vocabulary.py` scans `src/aml_triage/ui/**/*.py` and `specs/002-batch-triage-ui/contracts/ui-contract.md`; `tests/test_core_without_optional.py` asserts that importing `aml_triage.cli` and running `--help` never imports `aml_triage.ui` or `streamlit` (check `sys.modules`)
  - Milestone M2 / Type: tests / Depends: T004
  - Files: `tests/test_vocabulary.py`, `tests/test_core_without_optional.py`
  - Accept: both tests pass with and without the UI extras installed
  - Verify: `.venv/bin/pytest tests/test_vocabulary.py tests/test_core_without_optional.py -q`

**Checkpoint**: environment and skeleton ready; commit `chore(ui): pinned UI extras, config, make targets, skeleton, guard tests`.

---

## Phase 2: Foundational — batch endpoint (Milestone 1)

**Purpose**: `POST /score-batch` and `GET /triage-config` on the existing service, with the ranking
rule and per-row validation as pure functions. Every user story calls these.

**⚠️ CRITICAL**: no UI work starts until this phase is green.

- [ ] T006 [P] Add batch fixtures to `tests/api/conftest.py`: `batch_rows` (≥ 30 valid rows built from `make_synthetic_frame` incl. the causal aggregate columns), `invalid_rows` (one row per failure type: missing required field, non-numeric amount, negative amount, unknown `type`, extra field, `step` 0), `tie_rows` (identical scores, different `step`/position), and a helper that posts a batch and returns the parsed body
  - Milestone M1 / Type: tests / Depends: none
  - Files: `tests/api/conftest.py`
  - Accept: fixtures build in < 5 s from the existing `api_bundle`; no real data
  - Verify: `.venv/bin/pytest tests/api -q --co | grep -c batch`
- [ ] T007 [P] Write failing contract tests in `tests/api/test_batch_api.py`: (a) `/triage-config` shape and values equal the bundle's operating point; (b) `/score-batch` response validates against `contracts/batch-scoring-api.yaml` keys and `additionalProperties: false` (unknown top-level field → 422); (c) per-row validation: each `invalid_rows` case appears in `skipped` with `input_row`, `field`, `reason`, valid rows still scored; (d) ranking parity: `rank_batch` equals `evaluation.capacity.rank_within_periods` on a single-period frame incl. `tie_rows`; (e) priority rule: >K rows all above threshold → exactly K `high`; all below threshold → no `high`; fewer than K rows → `high` ≤ above-threshold count; one valid row → `ranked=false`, `rank=null`, priority equals `/score`; (f) every row's `risk_score` equals `/score` for the same row; (g) `len > batch_limit` → 413 naming the limit (set `AML_BATCH_LIMIT` small via monkeypatch); empty list → 422; (h) no prohibited field names in any response; (i) a scoring run makes no call into `data/` (monkeypatch `builtins.open`/`pandas.read_parquet` sentinel or assert no path under `data/` is opened)
  - Milestone M1 / Type: tests / Depends: T006
  - Files: `tests/api/test_batch_api.py`
  - Accept: tests are collected and FAIL for want of the endpoint (not for fixture errors)
  - Verify: `.venv/bin/pytest tests/api/test_batch_api.py -q` (expected: failures/errors on missing endpoint)
- [ ] T008 Add response/request models to `src/aml_triage/api/schemas.py`: `BatchRequest` (`transactions: list[dict]`, `explain: Literal["high","none","all"]="high"`, `extra="forbid"`), `ValidationIssue`, `ScoredRow` (`rank: int | None`), `OperatingPoint`, `Counts`, `BatchResponse`, `TriageConfig`, all `extra="forbid"`, field descriptions copied from the contract
  - Milestone M1 / Type: code / Depends: T007
  - Files: `src/aml_triage/api/schemas.py`
  - Accept: models round-trip the contract example; no field named in `PROHIBITED_OUTPUT_FIELDS`
  - Verify: `.venv/bin/pytest tests/api/test_batch_api.py -q -k "shape or prohibited"`
- [ ] T009 Implement pure functions in `src/aml_triage/api/batch.py`: `validate_rows(rows) -> (valid: list[tuple[input_row, TransactionRequest]], issues: list[ValidationIssue])` using `TransactionRequest.model_validate` per row and mapping pydantic errors to `field`/`reason`; `rank_batch(raw_scores, steps, input_rows) -> ranks` (sort keys score desc, step asc, input_row asc, mergesort); `assign_batch_priority(rank, raw, primary_k, threshold, decimals=OPERATING_POINT_DECIMALS)`
  - Milestone M1 / Type: code / Depends: T008
  - Files: `src/aml_triage/api/batch.py`
  - Accept: T007 (c), (d), (e) unit-level assertions pass when called directly; functions have no I/O
  - Verify: `.venv/bin/pytest tests/api/test_batch_api.py -q -k "parity or priority or validation"`
- [ ] T010 Extend `src/aml_triage/api/service.py`: `score_many(rows: list[dict]) -> (raw: np.ndarray, display: np.ndarray, X: pd.DataFrame)` building one feature frame and one `predict_proba`/calibrator call; `explain_row(X, i)` reusing `explain`; `batch_limit` read once from env `AML_BATCH_LIMIT` (default 5000, validated int ≥ 1); unknown `type` rows raise `UnknownTypeError` per row (caught by the orchestrator, not the request)
  - Milestone M1 / Type: code / Depends: T009
  - Files: `src/aml_triage/api/service.py`
  - Accept: `score_many([row])[1][0] == score(row)["risk_score"]` for every fixture row (SC-002 basis)
  - Verify: `.venv/bin/pytest tests/api/test_batch_api.py -q -k "equals_single"`
- [ ] T011 Implement `score_batch(service, request) -> BatchResponse` in `src/aml_triage/api/batch.py`: validate → score valid rows → rank (if ≥ 2) → priority → explanations per `explain` option (`high` band rows, `all`, or none) → counts → rows in rank order → disclaimer
  - Milestone M1 / Type: code / Depends: T010
  - Files: `src/aml_triage/api/batch.py`
  - Accept: T007 (b)–(f), (h) pass; single-row batch uses `service.priority`
  - Verify: `.venv/bin/pytest tests/api/test_batch_api.py -q`
- [ ] T012 Add endpoints to `src/aml_triage/api/main.py`: `GET /triage-config` and `POST /score-batch` (413 when `len(transactions) > service.batch_limit` with the limit in `detail`; 422 for empty list via `min_length=1`), operation descriptions carrying the disclaimer; bump app version to 0.2.0
  - Milestone M1 / Type: code / Depends: T011
  - Files: `src/aml_triage/api/main.py`
  - Accept: all of `tests/api` pass (existing 8 + new); `/docs` lists the two operations
  - Verify: `.venv/bin/pytest tests/api -q && make lint`
- [ ] T013 Parity check against the pipeline queue on real data (development machine only, plan V3 / SC-003): `scripts/check_batch_parity.py` loads the rows of review period 0 from `data/processed/test.parquet` + `features_primary_test.parquet`, posts them to a `TestClient` app in one batch, and compares the top-K `input_row` set and priorities with `reports/review_queue_period_0.md`; print the difference count; record the result in `specs/002-batch-triage-ui/quickstart.md` §4
  - Milestone M1 / Type: verification / Depends: T012
  - Files: `scripts/check_batch_parity.py`, `specs/002-batch-triage-ui/quickstart.md`
  - Accept: 0 differences; the script refuses to run when `data/processed` is missing (never in CI)
  - Verify: `.venv/bin/python scripts/check_batch_parity.py`

**Checkpoint**: Milestone 1 done. Commit `feat(api): batch scoring endpoint with in-batch ranking and per-row validation (002 M1)`; open PR "Milestone 1"; after merge, realign.

---

## Phase 3: User Story 1 — Upload a CSV and see a ranked review queue (Priority: P1) 🎯 MVP

**Goal**: upload → validate structure → score → ranked queue with disclaimer.

**Independent Test**: `pytest tests/ui -q -k us1`; manually load `deployment/ui/example_batch.csv`.

- [ ] T014 [P] [US1] Create `tests/ui/conftest.py`: `pytest.importorskip("streamlit")`; `InProcessTriageClient` implementing the `TriageClient` protocol over `fastapi.testclient.TestClient(create_app(api_bundle))`; `app_test()` helper that builds `AppTest.from_file("src/aml_triage/ui/app.py")`, injects the client into `st.session_state["client"]`, and runs; CSV builders (valid example, unknown column, empty, over-limit, one-invalid-row); `fs_snapshot()` helper hashing the repository tree and `~/.streamlit`
  - Milestone M2 / Type: tests / Depends: T012
  - Files: `tests/ui/conftest.py`
  - Accept: fixtures import; the in-process client returns the same body as the HTTP path would
  - Verify: `.venv/bin/pytest tests/ui -q --co`
- [ ] T015 [P] [US1] Write failing tests in `tests/ui/test_inputs.py`: header normalisation (whitespace, case), unknown columns detected and named, empty/header-only detected, over-limit detected with the limit, `dest_is_merchant` parsing (true/false/1/0), optional columns defaulted, values kept as received (no coercion beyond parsing), `input_row` is 1-based file position
  - Milestone M2 / Type: tests / Depends: none
  - Files: `tests/ui/test_inputs.py`
  - Accept: tests fail on missing module `aml_triage.ui.inputs`
  - Verify: `.venv/bin/pytest tests/ui/test_inputs.py -q`
- [ ] T016 [P] [US1] Write failing `AppTest` tests in `tests/ui/test_app.py` (US1 group): empty state shows sidebar config values (model version, K, threshold, batch limit) and the disclaimer; uploading the example CSV shows `counts.scored` rows in rank order with columns per `contracts/ui-contract.md`; the rule text and the below-capacity note appear; unknown-column file → refusal message naming the column, no table; the disclaimer appears in the sidebar and the footer in every state; no widget label or column matches the prohibited-action or prohibited-field lists
  - Milestone M2 / Type: tests / Depends: T014
  - Files: `tests/ui/test_app.py`
  - Accept: tests fail on missing `app.py`
  - Verify: `.venv/bin/pytest tests/ui/test_app.py -q -k us1`
- [ ] T017 [US1] Implement `src/aml_triage/ui/client.py`: `TriageClient` protocol (`config()`, `score_batch(rows, explain)`, `score_one(row)`), `HttpTriageClient` (requests, base URL and timeout from `configs/ui.yaml`, loopback default), typed errors `ServiceUnavailable`, `BatchTooLarge(limit)`, `BadRequest(detail)`
  - Milestone M2 / Type: code / Depends: T014
  - Files: `src/aml_triage/ui/client.py`
  - Accept: `InProcessTriageClient` and `HttpTriageClient` share the protocol; no logging of payloads
  - Verify: `.venv/bin/pytest tests/ui -q -k client`
- [ ] T018 [US1] Implement `src/aml_triage/ui/inputs.py`: `read_csv_rows(buffer, limit) -> list[dict] | StructuralError`, header normalisation, structural checks (unknown columns, empty, over limit, unreadable), row dicts with `input_row`, optional defaults, boolean parsing; values passed through as strings/numbers without other transformation (FR-013)
  - Milestone M2 / Type: code / Depends: T015
  - Files: `src/aml_triage/ui/inputs.py`
  - Accept: `tests/ui/test_inputs.py` passes
  - Verify: `.venv/bin/pytest tests/ui/test_inputs.py -q`
- [ ] T019 [US1] Implement `src/aml_triage/ui/views.py` for US1: `sidebar(config, status)`, `summary(result)`, `rule_text(result)` (RULE_TEXT plus BELOW_CAPACITY / SINGLE_ROW when applicable), `queue_table(rows_in, result)` (columns `rank, review_priority, risk_score, type, amount, step, input_row, model_version`; `st.dataframe`, sortable; rank column values fixed), `footer()`
  - Milestone M2 / Type: code / Depends: T017
  - Files: `src/aml_triage/ui/views.py`
  - Accept: helpers render with `AppTest`; every string comes from `texts.py`
  - Verify: `.venv/bin/pytest tests/ui/test_app.py -q -k "sidebar or queue"`
- [ ] T020 [US1] Implement `src/aml_triage/ui/app.py`: session state machine S0→S1→S2 (data-model §8), client from `st.session_state` or `HttpTriageClient`, `/triage-config` fetch with SERVICE_DOWN handling, "Upload CSV" tab with `st.file_uploader`, "Score batch" and "Clear batch" buttons, wiring of views; the batch is kept only in `st.session_state`; no `st.cache_*` on user data
  - Milestone M2 / Type: code / Depends: T018, T019
  - Files: `src/aml_triage/ui/app.py`
  - Accept: US1 tests pass; `make ui` renders against a running `make api`
  - Verify: `.venv/bin/pytest tests/ui -q -k us1`
- [ ] T021 [P] [US1] Ship the synthetic example: copy `specs/002-batch-triage-ui/contracts/examples/example_batch.csv` to `deployment/ui/example_batch.csv` (already whitelisted in `.gitignore`) and add a "Load synthetic example" button in the upload tab that reads it from the package path; label it synthetic on screen
  - Milestone M2 / Type: code / Depends: T020
  - Files: `deployment/ui/example_batch.csv`, `src/aml_triage/ui/app.py`
  - Accept: pressing the button yields the same S2 state as uploading the file; `make check-no-data` still passes
  - Verify: `.venv/bin/pytest tests/ui -q -k example && make check-no-data`

**Checkpoint**: MVP. Commit `feat(ui): CSV upload and ranked review queue (002 US1)`.

---

## Phase 4: User Story 2 — Enter several transactions by hand (Priority: P2)

**Goal**: manual grid with the same columns, same validation and scoring path.

**Independent Test**: `pytest tests/ui -q -k us2`; type three rows, one emptying the origin account.

- [ ] T022 [P] [US2] Write failing `AppTest` tests (US2 group) in `tests/ui/test_app.py`: manual grid with three rows scores identically to uploading the same rows as CSV; a manual row with a missing required value appears in the validation report while the others score; a single manual row shows the SINGLE_ROW note and a null rank
  - Milestone M2 / Type: tests / Depends: T020
  - Files: `tests/ui/test_app.py`
  - Accept: tests fail on the missing tab
  - Verify: `.venv/bin/pytest tests/ui/test_app.py -q -k us2`
- [ ] T023 [US2] Implement the "Enter rows" tab: `st.data_editor` with the schema columns and defaults (`inputs.grid_to_rows(df) -> list[dict]` assigning `input_row` from grid position) in `src/aml_triage/ui/inputs.py`; tab wiring in `src/aml_triage/ui/app.py` so both tabs feed the same S1 state
  - Milestone M2 / Type: code / Depends: T022
  - Files: `src/aml_triage/ui/inputs.py`, `src/aml_triage/ui/app.py`
  - Accept: US2 tests pass; no separate validation code for manual rows
  - Verify: `.venv/bin/pytest tests/ui -q -k "us1 or us2"`

**Checkpoint**: commit `feat(ui): manual multi-row entry (002 US2)`.

---

## Phase 5: User Story 3 — Understand why a row is where it is (Priority: P3)

**Goal**: per-row factors in plain language, identical to the single-transaction service.

**Independent Test**: `pytest tests/ui -q -k us3`; select the top row and a low row.

- [ ] T024 [P] [US3] Write failing `AppTest` tests (US3 group): selecting a row shows up to five factors, direction, and plain-language sentences equal to `POST /score` for that row (via the in-process client); a high-band row uses factors from the batch response, a low row triggers `score_one`; the panel shows rank, priority, score, model version, and the disclaimer; no prohibited vocabulary in the sentences
  - Milestone M2 / Type: tests / Depends: T020
  - Files: `tests/ui/test_app.py`
  - Accept: tests fail on the missing panel
  - Verify: `.venv/bin/pytest tests/ui/test_app.py -q -k us3`
- [ ] T025 [US3] Implement `explanation_panel(selected, rows_in, result, client)` in `src/aml_triage/ui/views.py` with an `input_row` selector, on-demand `client.score_one` for rows without factors, and a per-session `explanations` dict in `st.session_state`; wire into `src/aml_triage/ui/app.py`
  - Milestone M2 / Type: code / Depends: T024
  - Files: `src/aml_triage/ui/views.py`, `src/aml_triage/ui/app.py`
  - Accept: US3 tests pass; only one scoring path is used (no SHAP import in the UI)
  - Verify: `.venv/bin/pytest tests/ui -q -k us3 && ! grep -rn "import shap" src/aml_triage/ui`

**Checkpoint**: commit `feat(ui): per-row explanation panel (002 US3)`.

---

## Phase 6: User Story 4 — Export the ranked queue (Priority: P4)

**Goal**: two CSV downloads per `contracts/export-format.md`, disclaimer in both.

**Independent Test**: `pytest tests/ui -q -k "us4 or export"`.

- [ ] T026 [P] [US4] Write failing tests in `tests/ui/test_export.py`: first line `# ` + disclaimer verbatim; queue header equals the contract column list; rows in ascending rank; row count equals `counts.scored`; input values echoed as received; skipped file rows equal `len(skipped)`; UTF-8 BOM present; no prohibited field names or vocabulary; file names `triage_queue_<version>.csv` / `triage_skipped_<version>.csv`
  - Milestone M2 / Type: tests / Depends: T014
  - Files: `tests/ui/test_export.py`
  - Accept: tests fail on missing `aml_triage.ui.export`
  - Verify: `.venv/bin/pytest tests/ui/test_export.py -q`
- [ ] T027 [US4] Implement `src/aml_triage/ui/export.py`: `queue_csv(rows_in, result) -> bytes`, `skipped_csv(rows_in, result) -> bytes`, `file_names(version)`; built in memory only
  - Milestone M2 / Type: code / Depends: T026
  - Files: `src/aml_triage/ui/export.py`
  - Accept: `tests/ui/test_export.py` passes
  - Verify: `.venv/bin/pytest tests/ui/test_export.py -q`
- [ ] T028 [US4] Add the two `st.download_button` controls to S2 in `src/aml_triage/ui/app.py` (skipped download only when `skipped` is non-empty) and an `AppTest` test (US4 group) asserting the download payloads equal `export.queue_csv`/`skipped_csv` output
  - Milestone M2 / Type: code + tests / Depends: T027
  - Files: `src/aml_triage/ui/app.py`, `tests/ui/test_app.py`
  - Accept: US4 tests pass; nothing written to disk by the download path
  - Verify: `.venv/bin/pytest tests/ui -q -k "us4 or export"`

**Checkpoint**: commit `feat(ui): ranked-queue and skipped-rows exports (002 US4)`.

---

## Phase 7: User Story 5 — Clear feedback on bad input (Priority: P5)

**Goal**: per-row validation report; structural refusals with exact messages; no persistence.

**Independent Test**: `pytest tests/ui -q -k us5`.

- [ ] T029 [P] [US5] Write failing `AppTest` tests (US5 group): a CSV with one row per failure type shows each row in the validation report with `input_row`, `field`, `reason`, and the valid rows are scored; over-limit file → OVER_LIMIT message with the service's limit and no table; empty/header-only → EMPTY_FILE; non-UTF-8 bytes → UNREADABLE; unreachable service (client raising `ServiceUnavailable`) → SERVICE_DOWN with the `make api` hint and disabled inputs
  - Milestone M2 / Type: tests / Depends: T020
  - Files: `tests/ui/test_app.py`
  - Accept: tests fail on the missing report/expander
  - Verify: `.venv/bin/pytest tests/ui/test_app.py -q -k us5`
- [ ] T030 [US5] Implement `validation_report(result)` (expander titled with the skipped count, one line per issue) and the structural/service error messages in `src/aml_triage/ui/views.py`; wire into `src/aml_triage/ui/app.py`
  - Milestone M2 / Type: code / Depends: T029
  - Files: `src/aml_triage/ui/views.py`, `src/aml_triage/ui/app.py`
  - Accept: US5 tests pass; every message text is from `texts.py`
  - Verify: `.venv/bin/pytest tests/ui -q -k us5`
- [ ] T031 [US5] Add the no-persistence test (SC-007): `tests/ui/test_app.py::test_no_files_written` snapshots the repository tree and `~/.streamlit` before and after upload → score → select → export → clear, and asserts equality; also asserts `browser.gatherUsageStats` is false in `.streamlit/config.toml`
  - Milestone M2 / Type: tests / Depends: T030
  - Files: `tests/ui/test_app.py`
  - Accept: passes; if Streamlit writes a credentials/telemetry file, adjust config and re-run
  - Verify: `.venv/bin/pytest tests/ui -q -k no_files_written`

**Checkpoint**: Milestone 2 done. Commit `feat(ui): validation report, structural refusals, no-persistence test (002 US5)`; run the full suite `make lint && make test && make ui-test`; open PR "Milestone 2"; after merge, realign.

---

## Phase 8: User Story 6 — Run it locally from documented commands (Priority: P6, Milestone 3)

**Goal**: CI job, deployment guide, README, GenAI record, MLOps plan, timing, demo, quickstart run.

**Independent Test**: follow `specs/002-batch-triage-ui/quickstart.md` §1–§7 on a clean environment.

- [ ] T032 [P] [US6] Add the `ui-optional` job to `.github/workflows/ci.yml` (detect `src/aml_triage/ui/app.py`; Python 3.11; uv; `uv pip sync --system requirements.txt requirements-dev.txt requirements-api.txt requirements-ui.txt`; `uv pip install --system --no-deps -e .`; `pytest tests/ui tests/api -q`); leave `core` and `api-optional` unchanged
  - Milestone M3 / Type: config / Depends: T031
  - Files: `.github/workflows/ci.yml`
  - Accept: pushed branch shows the job green; `core` still green with optional tests skipped
  - Verify: GitHub Actions run on the branch head (checked via the API as in earlier milestones)
- [ ] T033 [P] [US6] Add `scripts/time_batch.py` (synthetic rows via `make_synthetic_frame`; times `POST /score-batch` in-process for 5,000 rows with `explain=high` and the `AppTest` render) and record the measured seconds in the deployment guide (plan V1 / SC-006)
  - Milestone M3 / Type: verification / Depends: T031
  - Files: `scripts/time_batch.py`, `deployment/DEPLOYMENT.md`
  - Accept: the guide states the measured numbers with machine and date; no real data used
  - Verify: `.venv/bin/python scripts/time_batch.py --rows 5000`
- [ ] T034 [US6] Write the "Batch triage UI" section of `deployment/DEPLOYMENT.md`: what it is, setup (`make setup-ui`), run (`make api`, `make ui`), the example file, the batch rule in plain words (FR-020), the batch limit and the measured time (T033), the privacy statement (in-memory only, telemetry off, loopback), limits, and the framework statement: FastAPI is the Step 8 deployment of record, Streamlit is the optional UI, why (research R-01)
  - Milestone M3 / Type: docs / Depends: T033
  - Files: `deployment/DEPLOYMENT.md`
  - Accept: `grep -n "deployment of record" deployment/DEPLOYMENT.md` matches; vocabulary test passes
  - Verify: `.venv/bin/pytest tests/test_vocabulary.py -q && grep -n "deployment of record" deployment/DEPLOYMENT.md`
- [ ] T035 [P] [US6] Update `README.md`: optional-steps status line for the batch UI, the three make targets in the Commands block, the framework statement (FR-062), a pointer to the deployment guide section; keep the repository map current (`src/aml_triage/ui/`, `deployment/ui/`)
  - Milestone M3 / Type: docs / Depends: T031
  - Files: `README.md`
  - Accept: every `make` target named in the README exists; disclaimer unchanged
  - Verify: `grep -oE 'make [a-z-]+' README.md | sort -u | while read -r m t; do make -n $t >/dev/null || echo "missing $t"; done`
- [ ] T036 [P] [US6] Update `docs/genai_usage.md` with a new use entry for this feature (tool and model, purpose, representative prompts incl. the clarification questions, human review performed, errors found and fixed) and `docs/mlops_plan.md` (UI versioned with the bundle it displays, effect of a bundle rollback, what monitoring a real deployment would add for batch uploads)
  - Milestone M3 / Type: docs / Depends: T031
  - Files: `docs/genai_usage.md`, `docs/mlops_plan.md`
  - Accept: both keep the disclaimer; vocabulary test passes
  - Verify: `.venv/bin/pytest tests/test_vocabulary.py -q`
- [ ] T037 [US6] Demo capture: capture screenshots of the running UI with the synthetic example (`deployment/ui/shots/01_empty.png` … `05_export.png`; steps listed in the deployment guide), add `scripts/render_ui_demo.py` (Pillow: compose the PNGs into `deployment/ui/demo_ui.gif` with a caption strip carrying the disclaimer), render the GIF, and reference it from the deployment guide; review every frame for non-synthetic content before committing
  - Milestone M3 / Type: docs / Depends: T034
  - Files: `scripts/render_ui_demo.py`, `deployment/ui/shots/*.png`, `deployment/ui/demo_ui.gif`, `deployment/DEPLOYMENT.md`
  - Accept: GIF under 6 MB (pre-commit size hook); frames show only the example batch
  - Verify: `.venv/bin/python scripts/render_ui_demo.py deployment/ui/shots deployment/ui/demo_ui.gif && ls -la deployment/ui/demo_ui.gif`
- [ ] T038 [US6] Removability and core isolation (SC-008): in a scratch venv with only `requirements.txt` + `requirements-dev.txt`, run `make test` and `make smoke` (expect green; `tests/ui` and `tests/api` skipped); then, in a scratch clone with `src/aml_triage/ui/`, `tests/ui/`, `requirements-ui.*`, `.streamlit/`, `configs/ui.yaml` deleted, run `make test` (expect green). Record both results in `specs/002-batch-triage-ui/quickstart.md` §6
  - Milestone M3 / Type: verification / Depends: T031
  - Files: `specs/002-batch-triage-ui/quickstart.md`
  - Accept: both runs green; no core module imports `aml_triage.ui`
  - Verify: `grep -rn "aml_triage.ui" src/aml_triage --include=*.py | grep -v "^src/aml_triage/ui/"` prints nothing
- [ ] T039 [US6] Execute `specs/002-batch-triage-ui/quickstart.md` §1–§7 end to end on this machine (service + UI + browser steps + headless tests), fix any drift in the quickstart, and fill the pass-criteria table with observed results
  - Milestone M3 / Type: verification / Depends: T032, T034, T035, T036, T037, T038
  - Files: `specs/002-batch-triage-ui/quickstart.md`
  - Accept: every expected outcome observed; SC-001..SC-009 each cite evidence
  - Verify: follow the quickstart

**Checkpoint**: Milestone 3 done. Commit `docs(ui): deployment guide, CI job, demo, docs, quickstart run (002 M3)`.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T040 Final audit for the new surfaces: `make lint && make test && make ui-test`; `pre-commit run --all-files`; vocabulary scan incl. UI texts and exports; disclaimer present in sidebar, footer, explanation panel, both exports, deployment guide section; `git ls-files` shows no uploads, exports, or data beyond the two whitelisted example CSVs; `make check-no-data`
  - Milestone M3 / Type: verification / Depends: T039
  - Files: none new
  - Accept: all green; no prohibited fields or vocabulary
  - Verify: `make lint && make test && make ui-test && .venv/bin/pre-commit run --all-files && make check-no-data`
- [ ] T041 Open the final PR for `002-batch-triage-ui` into `main` (title and body drafted by the assistant, PR ends with the session URL), merge with rebase, realign the branch, confirm CI on `main` incl. `ui-optional`; then decide with the user whether `make package` deliverables mention the UI (spec FR-084: report and decks unchanged unless asked)
  - Milestone M3 / Type: verification / Depends: T040
  - Files: none
  - Accept: `main` linear; feature branch ahead 0 / behind 0; CI green
  - Verify: `git rev-list --merges --count origin/main` = 0; Actions API shows success on the `main` head

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: starts immediately; T001 and T005 must pass before any UI test runs.
- **Foundational (Phase 2, M1)**: depends on nothing in Phase 1 except the repository; BLOCKS all
  user stories (every story calls the batch endpoint).
- **US1 (Phase 3)**: after Phase 2 and T001–T005. **MVP**.
- **US2, US3, US4, US5 (Phases 4–7)**: each depends on US1's `app.py` skeleton (T020); otherwise
  independent of one another (different views/functions; app.py edits are small and sequential).
- **US6 (Phase 8, M3)**: after Phases 3–7 (documents and packages the finished UI).
- **Polish (Phase 9)**: after Phase 8.

### Within each story

Tests first (they must fail), then pure functions, then views, then `app.py` wiring, then the
story's checkpoint commit with a green suite.

### Parallel Opportunities

- Phase 1: T002, T003, T004 in parallel; T005 after T004.
- Phase 2: T006 and T007 in parallel, then T008 → T009 → T010 → T011 → T012 → T013 sequentially.
- Phase 3: T014, T015, T016 in parallel (test files), T021 after T020.
- Phases 4–7: the four test tasks (T022, T024, T026, T029) can be written in parallel once T020
  exists; implementations touch `app.py` and must land sequentially.
- Phase 8: T032, T033, T035, T036 in parallel; T034 after T033; T037 after T034; T038 any time
  after T031; T039 last.

### Parallel example: Phase 3

```bash
Task: "tests/ui/conftest.py — in-process client, AppTest helper, CSV builders, fs snapshot"   # T014
Task: "tests/ui/test_inputs.py — CSV parsing and structural checks"                          # T015
Task: "tests/ui/test_app.py — US1 AppTest cases"                                             # T016
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 (T001–T005) and Phase 2 (T006–T013): batch endpoint green, parity with the pipeline
   queue confirmed on real data.
2. Phase 3 (T014–T021): CSV upload → ranked queue with disclaimer.
3. STOP and validate: `pytest tests/ui -q -k us1`, `make api & make ui`, load the example.

### Incremental delivery

Milestone 1 PR (Phase 2) → Milestone 2 PR (Phases 1, 3–7) → Milestone 3 PR (Phases 8–9). Each
PR: green `make lint && make test && make ui-test`, rebase-merge, realign `002-batch-triage-ui`.

---

## Notes

- Constitution reminders for every task: disclaimer verbatim from `aml_triage.constants`; no
  decision fields or actions; triage vocabulary; no dataset access from `aml_triage.api.batch` or
  `aml_triage.ui`; nothing persisted; optional component removable.
- Do not edit `specs/001-aml-risk-triage/**`, `configs/operating_point.yaml`, the released bundle,
  or the reports/decks (FR-084) during this feature.
- Linear-history routine after each merged PR: `git fetch origin && git checkout 002-batch-triage-ui
  && git reset --hard origin/main && git push --force-with-lease origin 002-batch-triage-ui &&
  git checkout main && git merge --ff-only origin/main && git checkout 002-batch-triage-ui`
  (verify trees identical first; if the branch has unmerged commits, `git rebase origin/main`).
- Commit trailer required: `Claude-Session: https://claude.ai/code/session_01FY3D285GvmwyT627E1yopq`.
