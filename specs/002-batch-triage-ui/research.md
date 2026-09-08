# Research: Batch Transaction-Risk Triage UI

**Date**: 2026-09-08 | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

Each entry: Decision, Rationale, Alternatives considered. Facts about the existing code were read
from the repository at commit `105f33a` (main after PR #8).

## R-01 UI framework and the Step 8 deployment of record

**Decision**: Build the UI with Streamlit as an optional component that calls the existing FastAPI
service over HTTP. FastAPI remains the Step 8 deployment of record; README and the deployment guide
state this explicitly.

**Rationale**: The brief requires local deployment via Flask, FastAPI, or Dash if Step 8 is
attempted; the FastAPI service already satisfies that and is unchanged in role. Streamlit gives
file upload, an editable grid, a sortable table, and download buttons without JavaScript, and ships
a headless test harness (`streamlit.testing.v1.AppTest`) so the UI can be tested in pytest and CI
without a browser. The constitution allows additional libraries when justified and pinned; the
justification is recorded in the plan's Complexity Tracking.

**Alternatives considered**: Dash (in the brief's list; callbacks and `dash.testing` need a browser
driver, heavier to test headlessly); FastAPI-served HTML + JavaScript (hand-written upload, sort,
export, and no test harness); Gradio (similar to Streamlit, weaker table interaction, less common in
this domain).

## R-02 Batch endpoint shape and per-row validation

**Decision**: `POST /score-batch` accepts `{"transactions": [object, …], "explain": "high"|"none"|"all"}`.
Each element is validated independently with the existing `TransactionRequest` model
(`extra="forbid"`), so a row with an unknown field, a missing field, a non-numeric value, or a
negative amount produces a per-row `ValidationIssue` instead of failing the request. An unknown
transaction type is caught per row from `UnknownTypeError`. Structural problems fail the whole
request: empty list → 422; more rows than the batch limit → 413 with the limit in the message.
`GET /triage-config` returns `model_version`, `batch_limit`, `primary_k`, `threshold`, `disclaimer`.

**Rationale**: The spec's skip-and-report rule (FR-012) is incompatible with a single pydantic
`list[TransactionRequest]` body, which rejects the whole payload on one bad row. Validating row by
row reuses the exact field rules of the single-transaction contract, so no second schema exists.
The batch limit must be enforced server-side (the service is the trust boundary) and exposed so
the UI shows the same number (FR-004) without a second configuration source.

**Alternatives considered**: extending `/score` to accept a list (breaks the 001 contract and its
`extra="forbid"` tests); a `mode=lenient` flag (two code paths); putting the limit in
`configs/ui.yaml` only (the service would not enforce it).

## R-03 Ranking rule and tie-break parity

**Decision**: `rank_batch()` in `aml_triage/api/batch.py` sorts by raw score descending, then
`step` ascending, then 1-based `input_row` ascending, with `kind="mergesort"`, and assigns ranks
1..n over the valid rows as a single period. `assign_batch_priority()` rounds the raw score to
`OPERATING_POINT_DECIMALS` (6) and applies the clarified rule: `high` if rank ≤ `primary_k` and
score ≥ `threshold`; `medium` if score ≥ `threshold`; else `low`. A batch with exactly one valid
row is not ranked (`ranked=false`, `rank=null`) and uses the existing `ScoringService.priority()`.

**Rationale**: `evaluation.capacity.rank_within_periods` uses the keys `period, score desc, step
asc, row_index asc` with mergesort; using the same keys with the batch as one period makes the
UI's order identical to the pipeline's for the same rows (SC-003), with `input_row` playing the
role of `row_index`. Rounding at the operating point's stored precision matches the fix in PR #8 so
the batch and single paths agree on bands. A test asserts `rank_batch` equals
`rank_within_periods` on a single-period frame.

**Alternatives considered**: calling `rank_within_periods` directly (needs a `period` column and
the review-period width, which is meaningless for an arbitrary upload); ranking by displayed
(calibrated) score (the calibrator collapses scores into plateaus and destroys the order; the
pipeline ranks on raw scores).

## R-04 Explanations on demand

**Decision**: The batch response carries `top_contributing_features` only for rows selected by the
`explain` option (default `"high"`: the high-band rows; `"all"` and `"none"` available). For any
other row the UI calls the existing `POST /score` for that single row when the investigator selects
it; since both paths use the same `ScoringService.explain`, the factors are identical.

**Rationale**: TreeExplainer per row costs milliseconds but 5,000 rows add seconds and payload;
the queue view needs scores and ranks immediately, factors only for the row being read. Using
`/score` for the on-demand case adds no code path and keeps FR-021 (single scoring path).

**Alternatives considered**: always explain all rows (slow at the limit); a separate
`/explain` endpoint (a second explanation surface to keep in sync).

## R-05 Export format

**Decision**: Two CSV downloads. The queue CSV's first line is `# ` followed by the disclaimer
verbatim; the second line is the header: `rank, review_priority, risk_score, input_row, <input
columns in schema order>, model_version`; rows in rank order. The skipped-rows CSV has the same
first line and the header `input_row, field, reason, <input columns as received>`. Both use UTF-8
with a BOM so spreadsheet applications open them cleanly.

**Rationale**: FR-040 requires the disclaimer in the file; a leading comment line keeps the data
rectangular for `pandas.read_csv(comment="#")` while staying visible when opened in a spreadsheet.
A disclaimer column repeated per row bloats the file and hides the text at the far right.

**Alternatives considered**: disclaimer column; Excel workbook with a second sheet (adds a
dependency and is not the spec's "CSV").

## R-06 Privacy configuration for Streamlit

**Decision**: Commit `.streamlit/config.toml` with `browser.gatherUsageStats = false`,
`server.headless = true`, `server.address = "127.0.0.1"`, `server.maxUploadSize = 10` (megabytes;
a 5,000-row batch of this schema is well under 1 MB, so 10 MB leaves headroom without inviting
files far above the batch limit), `logger.level = "error"`. Do not use `st.cache_data` or `st.cache_resource`
on any user data; keep the batch only in `st.session_state`. The `file_uploader` returns an
in-memory buffer; it is read once and not written anywhere. The service is contacted on loopback
only; the URL is in `configs/ui.yaml`.

**Rationale**: FR-050 forbids disk, log, cache, and telemetry writes of user data. Streamlit's
usage statistics are on by default and must be disabled explicitly; its caches are in-memory but
`cache_data` pickles values and is unnecessary here. A filesystem-snapshot test (SC-007) guards
the whole flow.

**Alternatives considered**: environment variables for the same settings (less visible than a
committed config file); disabling the uploader size limit (unnecessary).

## R-07 Pinning and compatibility

**Decision**: `requirements-ui.in` contains `-c requirements.txt`, `-c requirements-api.txt`,
`streamlit`, `requests`; compile with `uv pip compile requirements-ui.in -o requirements-ui.txt`.
The first Milestone 2 task installs the compiled file into the venv and runs a one-line `AppTest`
smoke to confirm the resolved Streamlit version imports and renders with pandas 3.0.5 on Python
3.11 (`[VERIFY]` V5). If it does not, pin the newest compatible release and record why.

**Rationale**: Constraints files keep pandas, numpy, pydantic, and fastapi at the versions the core
and API already use, so the UI cannot change the model environment. Compatibility of the latest
Streamlit with pandas 3 cannot be asserted from the repository; it must be verified by running.

**Alternatives considered**: adding Streamlit to `requirements-api.txt` (couples the deployment of
record to the UI); an unpinned install (violates P III).

## R-08 Headless UI testing

**Decision**: The session-scoped `api_bundle` fixture moves from `tests/api/conftest.py` to
`tests/conftest.py` (pytest scopes a conftest to its own directory tree, so `tests/ui/` cannot see
`tests/api/conftest.py`), keeping `pytest.importorskip("fastapi")` inside the fixture body.
`tests/ui/conftest.py` builds the FastAPI app from that fixture and provides an `InProcessTriageClient` (FastAPI `TestClient`) implementing
the same `TriageClient` protocol as the HTTP client. `tests/ui/test_app.py` uses
`streamlit.testing.v1.AppTest.from_file("src/aml_triage/ui/app.py")` and injects that client via
`st.session_state` before `run()`, then drives upload, scoring, row selection, and export, asserting
on rendered elements and texts. `tests/ui/test_inputs.py` and `test_export.py` test the pure
functions.

**Rationale**: `AppTest` runs the script in-process without a browser, so it works in CI and stays
deterministic. Injecting the client keeps the tests on the real scoring path (same bundle, same
functions) without sockets. All `tests/ui` modules `importorskip("streamlit")`, mirroring how
`tests/api` skips without FastAPI, so the core job remains green.

**Alternatives considered**: Playwright end-to-end tests (browser download, slow, flaky in CI);
mocking HTTP with canned responses (would not prove SC-002 equality).

## R-09 CI job shape

**Decision**: Add `ui-optional` to `.github/workflows/ci.yml`, modelled on `api-optional`: detect
`src/aml_triage/ui/app.py`, set up Python 3.11 and uv, `uv pip sync --system requirements.txt
requirements-dev.txt requirements-api.txt requirements-ui.txt`, `uv pip install --system --no-deps -e .`,
run `pytest tests/ui tests/api -q`. The `core` job is untouched and keeps running the full suite
without optional extras, which proves the skips work.

**Rationale**: Mirrors the established pattern; keeps optional dependencies out of the core
environment (P XI); runs the API tests again with the UI extras installed to catch pin conflicts.

**Alternatives considered**: extending `api-optional` (mixes two optional components; harder to
read in the CI summary).

## R-10 Demo capture

**Decision**: `scripts/render_ui_demo.py` composes a sequence of PNG screenshots
(`deployment/ui/shots/*.png`, captured by the developer from the running UI with the synthetic
example CSV) into `deployment/ui/demo_ui.gif` with Pillow, adding a caption strip with the
disclaimer. The deployment guide lists the exact capture steps. If a headless browser is available
on the machine, the same script MAY take the screenshots itself; this is optional.

**Rationale**: The existing GIF renderer draws terminal transcripts, not web pages; browser
automation crashed on this machine during upstream work (Comet headless). Screenshot composition
is deterministic, dependency-light, and honest about how the demo was produced (the guide says so).

**Alternatives considered**: Playwright screenshots (adds a browser download; can be tried as an
optional path); screen recording tools (not reproducible from the repository).
