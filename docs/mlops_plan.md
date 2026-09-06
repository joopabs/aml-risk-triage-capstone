# MLOps plan (optional Step 8)

> Educational prototype on synthetic data. This plan describes what is in place and what a real
> deployment would add; it does not claim production readiness.

## Reproducible environments

| In place | Notes |
|---|---|
| Python 3.11.12 pinned (`.python-version`) | `pyproject.toml` requires `>=3.11,<3.12` |
| Exact-version lockfiles compiled with `uv` | `requirements.txt` (runtime), `requirements-dev.txt`, `requirements-api.txt` |
| Global seed in config, propagated everywhere | `reproduce-check`: two fresh refits identical to the released bundle (tolerance 0.0) |
| Docker image for the scoring service | `deployment/Dockerfile`; copies only `src/`, `configs/`, and the released bundle; no data |
| One-command reproduction | `make setup && make data && make pipeline && make report` |

## Config-driven runs and experiment tracking

- Every run parameter lives in `configs/` (`base.yaml`, `schema.yaml`, `features.yaml`,
  `models/*.yaml`, `operating_point.yaml`); notebooks and scripts read from config (enforced by
  `tests/test_no_hardcoded_params.py`). Each artifact records the config hash.
- Experiment records already produced: per-run `models/runs/<id>__<set>/{val,test}_metrics.json`,
  tuning search logs `models/tuning/<id>_search.json`, comparison JSON under `reports/`.
- **Recommended tracker:** MLflow. Wiring is a small change: wrap `train_and_score` and
  `tune_candidate` in `mlflow.start_run`, log the config hash, params, the metric dict, and the
  bundle directory as an artifact. Not wired by default to keep the core pipeline dependency-light.

## CI checks

`.github/workflows/ci.yml` on every push and pull request: ruff lint and format; `detect-secrets`
against a baseline; 126 tests including leakage guards, the test-access state machine, the vocabulary
scan for determination language, and notebook compilation; coverage gate at 80% (currently ~92%);
a tracked-data check; and a smoke run of the complete 22-command pipeline on a synthetic sample
(no dataset download). The optional API job runs the contract tests when the API module exists.
Branch protection on `main`: pull requests only, required `core` check, no force-pushes.

## Monitoring plan (what a deployment would watch)

| Signal | How | Trigger |
|---|---|---|
| Score-distribution drift | daily histogram of raw scores vs the validation reference (KS statistic) | KS > threshold agreed with model risk |
| Prevalence per review period | positives confirmed by investigators per day | outside the range seen in validation/test |
| Recall@K on labelled batches | recompute `capacity_suite` on reviewed periods once labels arrive | drop below the validation ceiling minus tolerance |
| Slice error rates | regenerate the operational error-slice tables weekly | any slice's Recall@K below half the overall value for two weeks (seen for low-amount bands on test) |
| Feature reliance | permutation importance on a recent sample | one feature's drop > 0.3 (true today for both bookkeeping flags) |
| Latency and errors | uvicorn access logs, `/health` probe (container HEALTHCHECK) | p95 latency > 500 ms or non-200 rate > 1% |
| Override rate | investigator overrides per period from the human-in-the-loop workflow | sustained increase |

## Versioning and rollback

- Bundles are immutable directories `models/<UTC timestamp>-<git sha>-<candidate>/` with
  `pipeline.sha256`, `config_snapshot.yaml`, `metrics.json`, `feature_list.json`, `features.yaml`,
  and `model_card.md`. `models/LATEST` is a one-line pointer; every API response carries the version.
- **Rollback:** point `models/LATEST` at the previous bundle (or rebuild the image with
  `--build-arg MODEL_VERSION=<previous>`) and restart. No retraining is needed.
- **Re-release:** a new split/operating point requires a new config hash and a new bundle; the
  single-touch test protocol (`data/processed/test_access.json`) records any re-evaluation with a reason.

## Not in scope for this prototype

Authentication, batch endpoints, feature-store integration, A/B or shadow deployment, and any use
on real customer data (which requires the governance-controlled fairness audit in
`reports/bias_fairness_analysis.md`).
