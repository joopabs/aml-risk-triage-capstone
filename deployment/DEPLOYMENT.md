# Deployment guide — optional Step 8 (local scoring service)

> Educational decision-support prototype trained on synthetic PaySim data. The service returns a risk
> score and a review-priority recommendation for human investigator triage. It does not block
> transactions, close accounts, rate customers, file reports, or make AML determinations.

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
| Operating point | inside the bundle (`operating_point`) | raw-score threshold (medium) and K-th score cutoff (high); frozen on validation |
| Calibrator | inside the bundle | display probability only; priority bands use raw scores |
| `OMP_NUM_THREADS` | environment | CPU threads for the estimator |

## Model version, rollback, and audit

- Every response carries `model_version`. `models/LATEST` is a one-line pointer; to roll back,
  point it at a previous bundle directory (or rebuild the image with `--build-arg MODEL_VERSION=<old>`)
  and restart. Each bundle carries `pipeline.sha256`, `config_snapshot.yaml`, `metrics.json`,
  `feature_list.json`, `features.yaml`, and `model_card.md`.
- The single-touch test evaluation and any re-evaluation reasons are recorded in
  `data/processed/test_access.json`; the operating point is sealed in `configs/operating_point.yaml`.

## Limits

- Prototype scope: single-transaction scoring, no authentication, no persistence, no batching.
  Suitable for a local demo only.
- Priority bands for a single request use score-only cutoffs (no period rank exists for one
  transaction); the batch queue (`python -m aml_triage queue`) is the reference ranking.
- Results describe synthetic data. Real use requires the governance-controlled validation and
  fairness audit described in `reports/bias_fairness_analysis.md` and `docs/mlops_plan.md`.

## Demo

`deployment/demo/demo.gif` is a rendered terminal transcript of real responses from the running
service (health, a routine transfer, a drained-account transfer, and an invalid payload), produced by
`scripts/render_demo_gif.py` from `deployment/demo/transcript.json`. No screen recorder was used.
