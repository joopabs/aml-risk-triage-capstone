# UI Contract: Batch Transaction-Risk Triage UI

**Date**: 2026-09-08 | **Plan**: [../plan.md](../plan.md) | **Spec**: [../spec.md](../spec.md)

This is the behavioural contract for the Streamlit app (`src/aml_triage/ui/app.py`). Tests in
`tests/ui/test_app.py` assert it with `streamlit.testing.v1.AppTest`. Every user-visible string is
defined in `src/aml_triage/ui/texts.py` and is scanned by the vocabulary test; the disclaimer is
imported from `aml_triage.constants.DISCLAIMER` and never retyped.

## Layout

| Region | Content | Always present |
|---|---|---|
| Sidebar | Service status (reachable / unreachable), model version, frozen operating point (K, threshold), batch limit, synthetic-data notice, privacy notice ("processed in memory, not stored"), the disclaimer | yes |
| Header | Title "Batch Transaction-Risk Triage (educational prototype, synthetic data)" and one-line purpose | yes |
| Input area | Two tabs: "Upload CSV" and "Enter rows" | yes |
| Results area | Summary, rule text, queue table, explanation panel, downloads | after scoring |
| Footer | The disclaimer | yes |

## Screens and states

### S0 Empty

- Sidebar shows the service status. If `/triage-config` is unreachable: an error message with the
  exact command to start the service (`make api`) and no input controls enabled.
- Input area shows the expected columns (required and optional with defaults), the batch limit,
  the PRIVACY_NOTE as a caption directly under the file uploader (in addition to the sidebar), and
  a button to load the bundled synthetic example (`deployment/ui/example_batch.csv`).

### S1 Loaded (rows present, not scored)

- Shows the row count and the source (upload or manual); "Score batch" button; "Clear" button.
- Structural refusals (no rows loaded, message shown):
  - unknown columns: "Unknown columns: a, b. Only the schema columns are accepted."
  - empty file or header only: "Nothing to score: the file has no data rows."
  - over the limit: "This file has N rows; the batch limit is L rows."
  - unreadable file: "Could not read the file as UTF-8 CSV."

### S2 Scored

- Summary line: received, scored, skipped counts; high/medium/low counts; model version.
- Rule text (`texts.RULE_TEXT`): "Rows are ranked by model score within this batch. `high` means
  within review capacity K and at or above the validation-chosen threshold; `medium` means above
  the threshold but outside capacity; `low` otherwise. This is a review order, not a determination."
  When the batch has fewer valid rows than K: "This batch is below review capacity (K)."
  When one valid row: "A single row is not ranked; its priority uses the score bands."
- Queue table: columns `rank, review_priority, risk_score, type, amount, step, input_row,
  model_version`; sortable by the user; the `rank` values never change with sorting.
- Validation report (expander, present when `skipped` is non-empty): one line per issue with
  `input_row`, `field`, `reason`; count in the expander title.
- Explanation panel: a selector over `input_row` values of scored rows; shows up to five factors
  with direction and the plain-language sentence, the row's rank, priority, score, and the
  disclaimer. Factors come from the batch response when present, otherwise from `POST /score`
  for that row (same scoring path).
- Downloads: "Download ranked queue (CSV)" and, when skipped rows exist, "Download skipped rows
  (CSV)" per [export-format.md](export-format.md).
- "Clear batch" returns to S0 and drops all session data.

## What MUST NOT exist

- No control that records, applies, or simulates a decision on a transaction: no approve, block,
  hold, release, escalate, file, close, or rate buttons, checkboxes, or columns.
- No field named allow, block, decision, hold, sar, filing, or equivalents in any table or export.
- No text applying any phrase from `prohibited_applied_to_outputs` or `case_sensitive` in
  `configs/vocabulary.yaml` to a scored row; the positive class is "simulated fraud" where labels
  are discussed.
- No persistence: no save button, no history, no "recent batches", no cookies with row data.
- No accepted columns beyond the schema (unknown columns refuse the file; they are not dropped).

## Fixed texts (in `texts.py`)

| Key | Text |
|---|---|
| TITLE | Batch Transaction-Risk Triage (educational prototype, synthetic data) |
| PURPOSE | Orders a batch of synthetic PaySim-style transactions for human review using the released model and its frozen operating point. |
| PRIVACY_NOTE | Uploaded and typed data is processed in memory and is not stored, logged, or sent anywhere except the local scoring service. |
| SYNTHETIC_NOTE | PaySim is synthetic mobile-money data. It is not real SME, corporate, or Philippine banking data. |
| RULE_TEXT | (see S2) |
| BELOW_CAPACITY | This batch has fewer rows than the review capacity K. |
| SINGLE_ROW | A single row is not ranked; its priority uses the score bands of the single-transaction service. |
| SERVICE_DOWN | The scoring service is not reachable at {url}. Start it with `make api` and reload. |
| UNKNOWN_COLUMNS | Unknown columns: {cols}. Only the schema columns are accepted. |
| EMPTY_FILE | Nothing to score: the file has no data rows. |
| OVER_LIMIT | This file has {n} rows; the batch limit is {limit} rows. |
| UNREADABLE | Could not read the file as UTF-8 CSV. |
| DISCLAIMER | imported from `aml_triage.constants` |

## Test obligations (tests/ui/test_app.py)

1. Empty state shows sidebar config values from the service and the disclaimer.
2. Uploading the example CSV → S2 with `counts.scored` rows in the table in rank order.
3. Uploading a CSV with an unknown column → refusal message, nothing scored.
4. Uploading a CSV with one invalid row → the row appears in the validation report and the other
   rows are scored.
5. Manual entry of three rows → same result as uploading them.
6. Selecting a row → explanation panel content equals `POST /score` for that row.
7. Every rendered state contains the disclaimer text exactly once in the footer and once in the
   sidebar.
8. No widget label or table column matches the prohibited-action or prohibited-field lists.
9. Download payloads match [export-format.md](export-format.md).
10. Filesystem snapshot before/after the flow is unchanged (SC-007).
