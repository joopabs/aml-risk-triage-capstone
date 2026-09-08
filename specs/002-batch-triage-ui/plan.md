# Implementation Plan: Batch Transaction-Risk Triage UI

**Branch**: `002-batch-triage-ui` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-batch-triage-ui/spec.md` (clarified 2026-09-08)

**Upstream**: `specs/001-aml-risk-triage/` (complete). This plan adds to, and never modifies, the
released bundle, operating point, pipeline, reports, or decks.

## Summary

Add a batch scoring endpoint to the existing FastAPI service (`aml_triage.api`) that validates
rows individually, scores valid rows through the existing `ScoringService`, ranks them within the
batch with the pipeline's deterministic tie-break, and assigns review priority by the clarified rule
(`high` = rank ≤ K and raw score ≥ threshold; `medium` = score ≥ threshold; else `low`). Build a
Streamlit front end (`aml_triage.ui`) that uploads a CSV or takes manual rows, calls that endpoint,
shows the ranked queue, per-row factors, validation report, and exports, with the disclaimer on
every screen and nothing persisted. Ship it as a separate optional component (own pinned
requirements, own make targets, own optional CI job) while FastAPI remains the Step 8 deployment
of record.

## Technical Context

**Language/Version**: Python 3.11.12 (pyenv; `.python-version`), same as upstream.

**Primary Dependencies**: existing core stack (pandas 3.0.5, scikit-learn, SHAP, pydantic 2.13.5);
existing API extras (fastapi 0.141.1, uvicorn); new UI extras in `requirements-ui.in` →
`requirements-ui.txt` compiled with `uv pip compile -c requirements.txt -c requirements-api.txt`:
`streamlit`, `requests` (HTTP client to the service). Versions pinned at compile time
(`[VERIFY: streamlit release compatible with pandas 3.0.5 and Python 3.11; see research R-07]`).

**Storage**: none. Uploaded rows, scores, and exports live only in process memory and the browser
download. No files, caches, or logs of user data (spec FR-050).

**Testing**: pytest. API: `tests/api/test_batch_api.py` with the session-scoped synthetic
`api_bundle` fixture, moved from `tests/api/conftest.py` to `tests/conftest.py` so `tests/ui/` can
use it too (pytest scopes a conftest to its directory), and FastAPI `TestClient`. UI: `tests/ui/`
using `streamlit.testing.v1.AppTest`
(headless, no browser) with the UI's HTTP client replaced by an in-process client over the same
FastAPI app, so UI tests exercise the real scoring path. Both directories `importorskip` their
optional dependency so the core suite stays green without them.

**Target Platform**: local machine (macOS/Linux), loopback only: service on `127.0.0.1:8000`,
UI on `127.0.0.1:8501`.

**Project Type**: web service extension + local web UI, inside the existing single Python package.

**Performance Goals**: interactive use on a laptop: a 5,000-row batch (the default limit) scores
and renders within `[MEASURED: seconds, task V1]`; explanations are on demand so batch scoring
cost is one `predict_proba` call per batch plus SHAP only for the rows requested.

**Constraints**: no retraining, no dataset access, no second model copy (single scoring path);
no persistence or telemetry; disclaimer verbatim from `aml_triage.constants.DISCLAIMER` on every
screen and export; no decision fields or actions; vocabulary scan extended to UI text.

**Scale/Scope**: one user, one batch at a time, ≤ 5,000 rows by default (env-configurable);
~3 new source modules for the API, ~5 for the UI, ~4 test modules, 3 doc updates, 1 CI job.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design (see end of this section).*

| Gate | Requirement (this feature) | Evidence planned |
|---|---|---|
| G1 Framing | UI is decision support for review ordering; K and threshold shown as the frozen operating point; no new metric claims | `spec.md` Business Context; UI sidebar text; deployment guide |
| G2 Provenance | No data files added; example CSV is synthetic and labelled; no identifiers accepted; secret scan unchanged | `deployment/ui/example_batch.csv` header comment; `tests/ui/test_export.py`; pre-commit |
| G3 Reproducibility | `requirements-ui.txt` pinned; `make ui`, `make ui-test` documented; deterministic ranking; optional CI job | Makefile, README, `.github/workflows/ci.yml` |
| G4 Leakage | No fitting; released `feature_pipeline` + `estimator` reused via `ScoringService`; no `data/` access | `tests/api/test_batch_api.py::test_no_data_directory_access`; grep in T-audit |
| G5–G6 Data quality/EDA/FE | Not applicable (no new data or features); per-row validation mirrors the request schema | `tests/api/test_batch_api.py` validation cases |
| G7 Models | Released model only; operating point read from the bundle at run time | `ScoringService.op`; `/triage-config` |
| G8 Explainability | Per-row top factors from the same explainer as `/score`; plain-language sentences reused | `tests/ui/test_app.py::test_explanation_panel_matches_single_score` |
| G9 Ethics & fairness | No new claims; UI shows synthetic-data notice; batch `high` rule explained in plain words | UI texts; deployment guide |
| G10 Human-in-the-loop | Disclaimer on every screen/export; `additionalProperties: false` responses; no action controls; vocabulary test covers `src/aml_triage/ui` | contract, `tests/test_vocabulary.py` extension, `tests/ui/test_app.py::test_no_decision_controls` |
| G11 Communication | README status + commands; deployment guide UI section; demo capture | README, `deployment/DEPLOYMENT.md`, `deployment/ui/demo_ui.gif` |
| G12 Optional transparency | Separate module, requirements, CI job; removable; FastAPI stated as deployment of record; GenAI record and MLOps plan updated | README, `docs/genai_usage.md`, `docs/mlops_plan.md`, `tests/test_core_without_optional.py` extension |

**Principle checks**: P II (no identifiers, in-memory only, telemetry off), P III (pinned, seeded
not needed: no stochastic component; SHAP TreeExplainer is deterministic), P IV (no fitting),
P VII (same explainer), P IX (outputs limited to score, priority, rank, version, factors,
disclaimer), P X (docs updated, PR flow), P XI (optional, separated, stated).

**Stack rule (Additional Constraints → Technology)**: Streamlit and `requests` are additional
libraries and MUST be justified in the plan. Justification is in research R-01 and the Complexity
Tracking table below. Pre-Phase-0 result: PASS with one justified addition.

## Project Structure

### Documentation (this feature)

```text
specs/002-batch-triage-ui/
├── spec.md
├── plan.md                        # this file
├── research.md                    # Phase 0: R-01..R-10
├── data-model.md                  # Phase 1: entities, validation, ranking rule
├── quickstart.md                  # Phase 1: run + validation scenarios (SC-001..SC-009)
├── contracts/
│   ├── batch-scoring-api.yaml     # OpenAPI: POST /score-batch, GET /triage-config
│   ├── ui-contract.md             # screens, controls, states, fixed texts
│   ├── export-format.md           # queue CSV and skipped-rows CSV layout
│   └── examples/
│       ├── batch_request.json
│       └── example_batch.csv
├── checklists/requirements.md
└── tasks.md                       # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/aml_triage/
├── api/
│   ├── schemas.py                 # + BatchRequest, BatchRow result, Skipped, BatchResponse, TriageConfig
│   ├── batch.py                   # NEW: per-row validation, rank_batch(), assign_batch_priority(), score_batch()
│   ├── service.py                 # + score_many(rows) (vectorised predict_proba; explain per requested row)
│   └── main.py                    # + POST /score-batch, GET /triage-config
└── ui/                            # NEW optional component (importable only with requirements-ui)
    ├── __init__.py
    ├── app.py                     # Streamlit entry: `streamlit run src/aml_triage/ui/app.py`
    ├── client.py                  # TriageClient protocol; HttpTriageClient (requests); errors
    ├── inputs.py                  # CSV parsing/normalisation, manual grid → rows, structural checks
    ├── export.py                  # queue CSV / skipped CSV builders (disclaimer line)
    ├── texts.py                   # every fixed UI string (scanned by the vocabulary test)
    └── views.py                   # render helpers: sidebar, summary, queue table, explanation panel

.streamlit/config.toml             # gatherUsageStats=false, maxUploadSize, headless, logger level
configs/ui.yaml                    # api_url, explain_default ("high"); batch limit comes from the service
requirements-ui.in / requirements-ui.txt
deployment/ui/example_batch.csv    # small synthetic example generated by scripts/make_ui_example.py (FR-005)
deployment/ui/shots/               # M3 screenshots of the running UI (synthetic example only)
deployment/ui/demo_ui.gif          # demo capture composed from the screenshots (M3)
scripts/check_batch_parity.py      # M1 developer-only parity check against reports/review_queue_period_0.md (reads data/; never in CI)
scripts/make_ui_example.py         # M2 generates the synthetic example batch from make_synthetic_frame
scripts/time_batch.py              # M3 timing at the batch limit on synthetic rows (V1)
scripts/render_ui_demo.py          # M3 composes deployment/ui/shots/*.png into demo_ui.gif
.env.example                       # + AML_BATCH_LIMIT (deployment setting, next to AML_MODELS_DIR)
tests/
├── conftest.py                    # shared api_bundle fixture (moved from tests/api/conftest.py in M2)
├── api/test_batch_api.py          # M1
├── ui/conftest.py                 # in-process client over the FastAPI app + api_bundle
├── ui/test_inputs.py              # M2
├── ui/test_export.py              # M2
├── ui/test_app.py                 # M2 (AppTest)
└── test_vocabulary.py             # extended to src/aml_triage/ui (M2)
Makefile                           # + setup-ui, ui, ui-test
.github/workflows/ci.yml           # + ui-optional job
deployment/DEPLOYMENT.md, README.md, docs/genai_usage.md, docs/mlops_plan.md  # M3
```

**Structure Decision**: single package, two optional sub-packages (`api` existing, `ui` new). The
UI never imports the model or SHAP; it talks to the service over HTTP (`client.py`), which keeps
one scoring path (FR-021) and makes the UI removable (FR-061). Ranking and validation live in
`api/batch.py` as pure functions so they are unit-tested without HTTP and reused by the endpoint.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Streamlit (not in the constitution's core stack; not in the brief's Flask/FastAPI/Dash list) | Fastest path to an upload + table + download UI with headless tests (`AppTest`); no JavaScript; runs locally | Dash (in the brief's list) needs callback wiring and has no equivalent headless test harness in the pinned stack; a FastAPI-served HTML page needs hand-written JS for upload/sort/export. FastAPI stays the deployment of record, so the brief's requirement is met regardless (R-01). |
| `requests` in the UI | Plain synchronous HTTP client for a Streamlit script | `httpx` is already a FastAPI test dependency, but `requests` is what Streamlit examples and users expect; either is fine — `requests` chosen for simplicity; pinned. |

## Milestones

### Milestone 1 — Batch endpoint, ranking rule, schemas, tests

**Goal**: `POST /score-batch` and `GET /triage-config` on the existing service; pure ranking and
validation functions; contract tests. No UI yet.

**Files**: `src/aml_triage/api/batch.py` (new), `src/aml_triage/api/schemas.py`,
`src/aml_triage/api/service.py`, `src/aml_triage/api/main.py`,
`specs/002-batch-triage-ui/contracts/batch-scoring-api.yaml` (authoritative),
`tests/api/test_batch_api.py`, `tests/api/conftest.py` (add a fixture producing a batch from the
synthetic frame incl. one row per validation failure type).

**Design**:
- Request `{"transactions": [obj, …], "explain": "high"|"none"|"all"}`; each row is validated
  independently with `TransactionRequest.model_validate` (extra fields → per-row error; unknown
  type → per-row error via `UnknownTypeError`); structural errors (empty list, over limit) → 422/413
  for the whole request.
- Batch limit from env `AML_BATCH_LIMIT` (default 5000) read once at service start; exposed by
  `/triage-config` with `model_version`, `primary_k`, `threshold`, `disclaimer`.
- `service.score_many(rows)`: build one feature frame, one `predict_proba`, one calibrator call;
  returns raw and display scores per row. Explanations via the existing `explain(X_row)` only for
  rows selected by the `explain` option.
- `batch.rank_batch(raw_scores, steps, input_rows)`: sort by raw score desc, step asc, input_row
  asc, `mergesort` (identical keys to `rank_within_periods` with one period); ranks 1..n.
- `batch.assign_batch_priority(rank, raw, K, threshold)`: rounds raw to
  `OPERATING_POINT_DECIMALS`; `high` if rank ≤ K and score ≥ threshold; `medium` if score ≥
  threshold; else `low`. One valid row → `ranked=false`, `rank=null`, existing `priority()`.
- Response `additionalProperties: false`; fields limited to rank, risk_score, review_priority,
  input_row, factors, model_version, operating point, counts, skipped, disclaimer.

**Dependencies**: upstream bundle fixture (`tests/api/conftest.py`), `requirements-api.txt`.

**Verification**:
```bash
pytest tests/api -q                                   # new tests: structure, validation, ranking, equality with /score, ties, <K, 1 row, limit, no data access
make lint && make test                                # core suite unaffected
python - <<'EOF'   # SC-003 on real data (dev machine only): rows of period 0 vs reports/review_queue_period_0.md
EOF
```
**Expected artifacts**: endpoints live under `make api`; contract file; tests green; `/docs` shows
the two new operations with the disclaimer in descriptions.

**Privacy controls**: request bodies never logged (uvicorn access log has paths only; no custom
logging of payloads); no writes; `input_row` is the only per-row identifier and is positional.

### Milestone 2 — Streamlit UI

**Goal**: upload CSV or enter rows, validation report, ranked queue, per-row factors, exports,
disclaimer everywhere; headless tests.

**Files**: `src/aml_triage/ui/{__init__,app,client,inputs,export,texts,views}.py`,
`.streamlit/config.toml`, `configs/ui.yaml`, `requirements-ui.in`, `requirements-ui.txt`,
`deployment/ui/example_batch.csv`, `tests/ui/{conftest,test_inputs,test_export,test_app}.py`,
`tests/test_vocabulary.py` (add `src/aml_triage/ui` to scanned paths),
`tests/test_core_without_optional.py` (assert core import graph excludes `aml_triage.ui`).

**Design**:
- `inputs.py`: read CSV (UTF-8, `pandas.read_csv(dtype=str)` to avoid silent coercion), normalise
  header whitespace/case, structural checks (unknown columns → refuse and name them; empty → refuse;
  > limit → refuse with the limit), build `list[dict]` rows preserving the 1-based input row number;
  manual grid via `st.data_editor` with the same columns and defaults.
- `client.py`: `TriageClient` protocol (`config()`, `score_batch(rows, explain)`, `score_one(row)`),
  `HttpTriageClient` (requests, timeout, loopback URL from `configs/ui.yaml`), typed errors for
  unreachable service / 413 / 422.
- `views.py`: sidebar (service status, model version, K, threshold, batch limit, privacy note,
  synthetic notice, disclaimer), summary counts, plain-words rule text (`texts.RULE_TEXT`), queue
  table (`st.dataframe`, sortable, rank column fixed), row selector → explanation panel (calls
  `score_one` for the selected row when factors were not returned in the batch), download buttons.
- `export.py`: queue CSV and skipped CSV per `contracts/export-format.md` (first line `#` +
  disclaimer; rank order; input columns echoed from the client-side rows).
- `texts.py`: every user-visible string; the vocabulary test scans it; the disclaimer is imported
  from `aml_triage.constants`, never retyped.
- `.streamlit/config.toml`: `browser.gatherUsageStats = false`, `server.headless = true`,
  `server.maxUploadSize` sized for the row limit, `logger.level = "error"`; no `st.cache_data`
  on user data; `st.session_state` only (process memory).

**Dependencies**: Milestone 1 endpoints; `requirements-ui.txt` compiled and installable
(`[VERIFY]` R-07).

**Verification**:
```bash
uv pip sync --python .venv/bin/python requirements.txt requirements-dev.txt requirements-api.txt requirements-ui.txt
pytest tests/ui -q                                    # AppTest: upload → queue → explanation → export; validation report; disclaimer present on every view; no action controls
pytest tests/test_vocabulary.py tests/test_core_without_optional.py -q
make api & make ui                                    # manual: load deployment/ui/example_batch.csv
```
**Expected artifacts**: running UI at `127.0.0.1:8501`; example CSV; tests green; vocabulary scan
covers UI texts.

**Privacy controls**: telemetry disabled by config; uploads held as in-memory buffers only; no
disk writes (test snapshots the repo and home dir before/after a scoring run: SC-007); no
`st.cache_data`/`st.cache_resource` on user data; loopback URL default; no identifiers accepted
(unknown columns refused, not dropped).

### Milestone 3 — Make targets, CI, deployment guide, demo, docs

**Goal**: documented, reproducible run; optional CI job; transparency of optional work.

**Files**: `Makefile` (`setup-ui`, `ui`, `ui-test`), `.github/workflows/ci.yml` (`ui-optional`
job mirroring `api-optional`, installing `requirements-ui.txt`, running `pytest tests/ui tests/api -q`),
`deployment/DEPLOYMENT.md` (new "Batch triage UI" section: setup, run, example, rule in plain
words, limit and measured time V1, privacy statement, limits, framework statement), `README.md`
(status line, commands, framework statement), `docs/genai_usage.md` (Use N: this feature),
`docs/mlops_plan.md` (UI versioning with the bundle, rollback effect, monitoring),
`deployment/ui/demo_ui.gif` (+ `scripts/render_ui_demo.py` composing captured screenshots, R-10),
`specs/002-batch-triage-ui/quickstart.md` executed end to end.

**Dependencies**: Milestones 1–2.

**Verification**:
```bash
make -n setup-ui ui ui-test                           # targets exist
make ui-test                                          # = pytest tests/ui tests/api -q
make ci                                               # core unchanged and green
scripts/check_no_optional_dependency.sh               # or the extended test: core imports without streamlit/fastapi
git ls-files | grep -E 'uploads?|\.csv$' | grep -v example_batch.csv   # expect none
```
**Expected artifacts**: green CI with the new job; deployment guide section; demo GIF; README and
docs updated; quickstart pass table filled; PR.

**Privacy controls**: demo capture uses only the synthetic example CSV; screenshots reviewed
before commit for any non-synthetic content; no user data in docs.

## Phase 0 — Research

See [research.md](research.md): R-01 framework choice (Streamlit, FastAPI remains deployment of
record), R-02 batch endpoint shape and per-row validation, R-03 ranking rule implementation and
tie-break parity, R-04 explanation on demand, R-05 export format, R-06 privacy configuration for
Streamlit, R-07 pinning and compatibility, R-08 headless UI testing, R-09 CI job shape, R-10 demo
capture. All Technical Context unknowns are resolved there except the two `[VERIFY]`/`[MEASURED]`
items, which are validation tasks (V1, V5) and cannot be resolved before implementation.

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md): Batch, TransactionRow, ValidationIssue, ScoredRow, Explanation,
  QueueExport, TriageConfig; validation rules; ranking and priority rule; state of a batch in the
  UI session.
- [contracts/batch-scoring-api.yaml](contracts/batch-scoring-api.yaml): OpenAPI 3.1 for
  `POST /score-batch` and `GET /triage-config`, `additionalProperties: false` throughout.
- [contracts/ui-contract.md](contracts/ui-contract.md): screens, controls, states, fixed texts,
  what MUST NOT exist (action controls, decision fields).
- [contracts/export-format.md](contracts/export-format.md): both CSV layouts.
- [contracts/examples/](contracts/examples/): `batch_request.json`, `example_batch.csv`.
- [quickstart.md](quickstart.md): setup, run, validation scenarios mapped to SC-001..SC-009.

## Constitution Check — post-design re-evaluation

All gates remain PASS. The design adds no data, no fitting, no persistence, and no decision
surface. The one stack addition (Streamlit + requests) is justified above and isolated in
`requirements-ui.txt`, an optional CI job, and `src/aml_triage/ui/`; FastAPI remains the Step 8
deployment of record and the README/deployment guide will say so (FR-062). No Complexity
Tracking entry is unjustified. Ready for `/speckit-tasks`.

## Validation tasks carried into tasks.md

| ID | Item | Where resolved |
|---|---|---|
| V1 | `[MEASURED]` scoring + render time for a 5,000-row batch | M3, deployment guide |
| V2 | `[VERIFY]` no `data/` access from `aml_triage.api.batch` / `aml_triage.ui` | M1 test + M3 grep |
| V3 | SC-003 parity with `reports/review_queue_period_0.md` on real data (dev machine) | M1 script |
| V4 | Framework statement in README and deployment guide | M3 |
| V5 | `[VERIFY]` Streamlit pin compatible with pandas 3.0.5 / Python 3.11 (compile + AppTest run) | M2 first task |
