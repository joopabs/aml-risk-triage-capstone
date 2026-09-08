# Deployment guide — optional Step 8 (local scoring service)

> Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.
>
> The service returns a risk score and a review-priority recommendation for human investigator
> triage; it does not block transactions, close accounts, rate customers, file reports, or make AML
> determinations.

## What the service is

A FastAPI application (`src/aml_triage/api/`) that loads the released bundle `models/LATEST`
(currently `20260904T225142-0dc8f82-hgb`) once at start-up and scores single transactions with the bundle's
fitted feature pipeline, estimator, frozen operating point, and validation-fitted calibrator.
Contract: `specs/001-aml-risk-triage/contracts/scoring-api.yaml` (`GET /health`, `POST /score`).
Request bodies are never logged or persisted; identifiers are never sent (the caller supplies the
account type and the causal aggregates).

## Run locally

```bash
make setup                                  # if not done: venv + pinned dependencies
uv pip sync --python .venv/bin/python requirements.txt requirements-dev.txt requirements-api.txt
make pipeline                               # only if models/<version>/pipeline.joblib is absent (joblib files are never committed)
make api                                    # uvicorn on http://127.0.0.1:8000  (interactive docs at /docs)

curl -s localhost:8000/health
curl -s -X POST localhost:8000/score -H 'content-type: application/json' \
  -d @specs/001-aml-risk-triage/contracts/examples/score_request.json
```

An invalid payload (missing field, unknown field, unknown transaction type) returns HTTP 422 and no
score. The response schema forbids additional properties, so no decision field (allow, block, hold,
filing) can ever be emitted.

## Run in a container

```bash
make docker-build     # docker build -f deployment/Dockerfile --build-arg MODEL_VERSION=$(cat models/LATEST) .
make docker-run       # http://127.0.0.1:8000
```

The image (`deployment/Dockerfile`, `python:3.11-slim`) copies `src/`, `configs/`, and the single
released bundle directory. It contains no data (`.dockerignore` excludes `data/`, reports, notebooks,
tests). The bundle's `pipeline.joblib` must exist locally when building; regenerate it with
`make pipeline` and verify it against `models/<version>/pipeline.sha256`.

## Configuration

| Setting | Where | Effect |
|---|---|---|
| `AML_MODELS_DIR` | environment (default `models`) | directory holding `LATEST` and the bundles |
| `AML_BATCH_LIMIT` | environment (default `5000`) | maximum rows accepted by `POST /score-batch`; reported by `GET /triage-config` and shown in the UI |
| Operating point | inside the bundle (`operating_point`) | raw-score threshold (medium) and K-th score cutoff (high); frozen on validation |
| Calibrator | inside the bundle | display probability only; priority bands use raw scores |
| `OMP_NUM_THREADS` | environment | CPU threads for the estimator |

## Batch triage UI (optional, feature 002)

An interactive front end for scoring many synthetic transactions at once (`src/aml_triage/ui/`,
Streamlit). The FastAPI service above remains the Step 8 deployment of record (the brief allows
Flask, FastAPI, or Dash). The UI is an additional, removable local component: it
never loads the model and calls the service over the loopback interface, so there is one scoring
path. Streamlit was chosen over Dash for its file-upload, table, and download widgets without
JavaScript and for its headless test harness (`streamlit.testing.v1.AppTest`), which lets the UI be
tested in CI without a browser (`specs/002-batch-triage-ui/research.md`, R-01).

```bash
make setup-ui                               # core + dev + API + UI pinned requirements into .venv
make api                                    # terminal 1: the scoring service on :8000
make ui                                     # terminal 2: the UI on http://127.0.0.1:8501
make ui-test                                # headless UI + API tests
```

In the browser: press **Load synthetic example** (or upload `deployment/ui/example_batch.csv`, or
paste CSV lines under **Enter rows**), then **Score batch**. The queue lists every valid row in rank
order with its risk score, review priority, and the model version; select a row to see its top
factors in plain language; download the ranked queue and the skipped rows as CSV. `Clear batch`
drops everything. Opening `http://127.0.0.1:8501/?demo=example` loads and scores the example
automatically (used for the screenshots below).

**Batch rule (spec FR-020).** Rows are ranked by raw model score within the uploaded batch with the
pipeline's tie-break (score, then step, then position). A row is `high` when its rank is within the
review capacity K **and** its score is at or above the validation-chosen threshold, both read from the
frozen operating point at run time; `medium` when above the threshold but outside capacity; `low`
otherwise. A batch smaller than K therefore has at most as many `high` rows as above-threshold rows,
and a batch of routine transactions has none. A single row is not ranked and uses the score-only bands
of `POST /score`. On review period 0 of the test split (32,709 rows in one batch) the endpoint's
top-200 set, order, and priorities were identical to `reports/review_queue_period_0.md`
(`scripts/check_batch_parity.py`).

**Validation.** Rows are validated one by one by the service; an invalid row (missing field,
non-numeric or negative amount, unknown type, extra field) is listed with its row number, field, and
reason while the rest are scored. Only structural problems refuse the whole file: unknown or missing
columns, an empty file, or more rows than the batch limit.

**Batch limit and measured time.** Default 5,000 rows (`AML_BATCH_LIMIT`, enforced by the service
and shown in the UI). Measured on 2026-09-08 (Apple M3, released bundle, synthetic rows,
`scripts/time_batch.py --rows 5000`): `POST /score-batch` with factors for the high band 0.78 s;
headless UI parse and load 0.02 s, score and table render 0.14 s. The limit can be raised in the
environment if a machine has headroom.

**Privacy.** Uploaded and typed data stay in process memory: no disk writes, no logs of payloads,
no caches, Streamlit usage statistics disabled (`.streamlit/config.toml`), loopback only, 10 MB
upload cap. A test snapshots the repository and `~/.streamlit` before and after a full upload,
score, explain, export, clear cycle and asserts nothing changed. No identifiers are accepted: the
request schema has none, and unknown columns refuse the file rather than being dropped.

**Limits.** Local demo only: no authentication, one user, one batch at a time, nothing persisted;
explanations are computed for the high band in the batch call and on demand for other rows.

**Demo.** `deployment/ui/demo_ui.gif` is produced by `scripts/render_ui_demo.py`. On this machine
no headless browser could take screenshots, so the script drives the real app headlessly with
`streamlit.testing.v1.AppTest` against the released bundle in process and draws each state's actual
rendered text as a frame (empty state, example loaded, ranked queue, explanation panel, exports),
with the disclaimer strip under every frame; it is a rendered transcript of real UI states, the same
approach as the service demo, not a screen recording. To replace it with browser screenshots, save
PNG captures of the running app (synthetic example only, e.g. via `?demo=example`) into
`deployment/ui/shots/` and re-run the script; it composes PNGs when they exist.

## Model version, rollback, and audit

- Every response carries `model_version`. `models/LATEST` is a one-line pointer; to roll back,
  point it at a previous bundle directory (or rebuild the image with `--build-arg MODEL_VERSION=<old>`)
  and restart. Each bundle carries `pipeline.sha256`, `config_snapshot.yaml`, `metrics.json`,
  `feature_list.json`, `features.yaml`, and `model_card.md`.
- The single-touch test evaluation and any re-evaluation reasons are recorded in
  `data/processed/test_access.json`; the operating point is sealed in `configs/operating_point.yaml`.

## Limits

- Prototype scope: single-transaction scoring plus in-batch ranking (`POST /score-batch`, up to
  the batch limit), no authentication, no persistence. Suitable for a local demo only.
- Priority bands for a single request use score-only cutoffs (no period rank exists for one
  transaction), compared at the operating point's stored precision (6 decimals); the batch queue
  (`python -m aml_triage queue`) is the reference ranking.
- Results describe synthetic data. Real use requires the governance-controlled validation and
  fairness audit described in `reports/bias_fairness_analysis.md` and `docs/mlops_plan.md`.

## Demo

`deployment/demo/demo.gif` is a rendered terminal transcript of real responses from the running
service (health, a routine transfer, a drained-account transfer, and an invalid payload), produced by
`scripts/render_demo_gif.py` from `deployment/demo/transcript.json`. No screen recorder was used.
