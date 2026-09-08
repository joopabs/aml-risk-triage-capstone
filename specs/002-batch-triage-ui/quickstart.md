# Quickstart: Batch Transaction-Risk Triage UI

Run and validation guide for feature 002. Every command runs from the repository root on the
`002-batch-triage-ui` branch (or `main` after merge). Expected outcomes are the spec's success
criteria SC-001..SC-009; contract details live in [contracts/](contracts/).

## Prerequisites

- Upstream feature complete: `models/LATEST` points at a released bundle with `pipeline.joblib`
  present (regenerate with `make pipeline` if the joblib is missing; it is gitignored).
- Python 3.11.12, `uv`, and the core environment (`make setup`).

## 1. Install the optional extras (M2)

```bash
uv pip sync --python .venv/bin/python requirements.txt requirements-dev.txt requirements-api.txt requirements-ui.txt
# or: make setup-ui
python -c "import streamlit, fastapi; print(streamlit.__version__)"   # expected: the pinned version imports (V5)
```

## 2. Batch endpoint (M1)

```bash
make api &                                             # service on http://127.0.0.1:8000
curl -s localhost:8000/triage-config | jq              # expected: model_version, batch_limit 5000, primary_k, threshold, disclaimer
curl -s -X POST localhost:8000/score-batch -H 'content-type: application/json' \
  -d @specs/002-batch-triage-ui/contracts/examples/batch_request.json | jq
# expected: 3 scored rows in rank order (the emptied-account TRANSFER first), row 4 in `skipped`
#           with field "type" (unknown type WIRE), counts.received 4, disclaimer present,
#           no allow/block/decision field anywhere
pytest tests/api -q                                     # expected: pass, incl. ranking parity, equality with /score, ties, <K, single row, limit
```

## 3. UI (M2)

```bash
make ui                                                 # Streamlit on http://127.0.0.1:8501 (service must be running)
```

In the browser:

1. Sidebar shows service status, model version, K, threshold, batch limit, privacy and synthetic
   notices, and the disclaimer (SC-004).
2. "Upload CSV" → load `deployment/ui/example_batch.csv` → "Score batch". Expected: all rows
   appear once, in rank order, with risk score, priority, and model version (SC-001); the rule text
   and "below review capacity" note are shown (the example has fewer rows than K).
3. Select the top row → explanation panel lists up to five factors in plain language; compare with
   `curl -X POST localhost:8000/score` for the same row: identical factors and score (SC-002).
4. Upload a copy of the example with one column renamed → refusal naming the column; nothing scored.
   Upload a copy with `amount` set to `-5` on one row and `type` set to `WIRE` on another →
   both rows in the validation report with row number, field, and reason; the rest scored (SC-005).
5. "Enter rows" → type three rows (one emptying the origin account) → same result as uploading them.
6. "Download ranked queue (CSV)" and "Download skipped rows (CSV)" → first line is the disclaimer,
   header per `contracts/export-format.md`, rows in rank order.
7. Reload the page → empty state; `git status --porcelain` unchanged; no new files under the
   repository or the home directory (SC-007).

Headless equivalent:

```bash
pytest tests/ui -q                                      # expected: pass (AppTest drives steps 1–7 on the synthetic fixture bundle)
pytest tests/test_vocabulary.py tests/test_core_without_optional.py -q   # UI texts clean; core import graph excludes aml_triage.ui
```

## 4. Parity with the pipeline queue (V3, SC-003; development machine with real data)

```bash
python scripts/check_batch_parity.py                   # created in M1 (T013); loads review period 0 from data/processed
                                                        # (test split + primary features), posts one batch in-process, and
                                                        # compares the top-K set and priorities with reports/review_queue_period_0.md
# expected: 0 differences in the top-K set and their priorities; the script refuses to run without data/processed
```

## 5. Timing at the limit (V1, SC-006)

```bash
python scripts/time_batch.py --rows 5000              # created in M3 (T033); synthetic rows; prints seconds for /score-batch and for the UI render (AppTest)
# expected: recorded in deployment/DEPLOYMENT.md ("Batch triage UI" section)
```

## 6. Removability and CI (M3, SC-008)

```bash
uv pip sync --python .venv/bin/python requirements.txt requirements-dev.txt   # core env only
make test && make smoke                                 # expected: green; tests/ui and tests/api skipped
git stash -u  # optional: remove UI files locally and re-run `make test` to prove no core import of aml_triage.ui
```

CI: the `ui-optional` job installs the UI extras and runs `pytest tests/ui tests/api -q`; the
`core` job is unchanged.

## 7. Documentation (M3)

```bash
grep -n "deployment of record" README.md deployment/DEPLOYMENT.md   # expected: FastAPI named as the Step 8 deployment of record; Streamlit named as the UI
ls deployment/ui/demo_ui.gif deployment/ui/example_batch.csv
make package                                             # unchanged deliverables; the UI is not part of the submission files
```

## Pass criteria summary

| Check | Expected |
|---|---|
| `pytest tests/api tests/ui -q` with extras | all pass |
| `make test` without extras | all pass, optional tests skipped |
| Batch vs single scores | 0 differences (SC-002) |
| Batch vs queue report, period 0 | 0 differences in top-K set and priorities (SC-003) |
| Disclaimer | on every screen and in both exports (SC-004) |
| Invalid rows | listed with row, field, reason; valid rows scored (SC-005) |
| Files written by a scoring run | none (SC-007) |
| Timing at 5,000 rows | measured and recorded (SC-006) |
