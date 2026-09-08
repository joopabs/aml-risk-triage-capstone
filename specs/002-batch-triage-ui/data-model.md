# Data Model: Batch Transaction-Risk Triage UI

**Date**: 2026-09-08 | **Plan**: [plan.md](plan.md)

Nothing here is persisted. Every entity exists in the service's request/response cycle or in the
UI's session memory and is gone when the batch is cleared or the page reloads.

## 1. TransactionRow (input)

The fields of the upstream single-transaction request (`TransactionRequest`,
`specs/001-aml-risk-triage/contracts/scoring-api.yaml`), plus a positional identifier.

| Field | Type | Rule |
|---|---|---|
| input_row | int ≥ 1 | 1-based position in the uploaded file (excluding header) or manual grid; assigned by the UI, echoed by the service; the only row identifier |
| step | int ≥ 1 | required |
| type | string | required; must be one of the types known to the released bundle (from the fitted one-hot encoder) |
| amount | number ≥ 0 | required |
| oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest | number | required |
| orig_prior_txn_count, dest_prior_txn_count | int ≥ 0 | optional, default 0 |
| orig_prior_amount_sum, dest_prior_amount_sum | number ≥ 0 | optional, default 0.0 |
| dest_is_merchant | boolean | optional, default false; CSV accepts true/false/1/0 (case-insensitive) |

Any other column or field is an error: for a CSV, unknown columns refuse the whole file
(structural); for a JSON row sent to the service, an unknown field is a per-row ValidationIssue.

## 2. Batch (request)

| Field | Type | Rule |
|---|---|---|
| transactions | array of objects | 1 ≤ length ≤ batch_limit; each object validated independently as a TransactionRow (without input_row; the position in the array + 1 is the input_row) |
| explain | enum `high` / `none` / `all` | default `high`; which rows receive factors in the response |

Structural failures (whole request, nothing scored): empty array → 422; length > batch_limit →
413 with the limit in the message; malformed JSON → 422.

## 3. ValidationIssue

| Field | Type | Meaning |
|---|---|---|
| input_row | int | position of the failing row |
| field | string | field name, or `_row` for row-level problems (unknown type is reported on `type`) |
| reason | string | plain reason from the validator, e.g. "Field required", "Input should be greater than or equal to 0", "type must be one of [...]" |

A row may produce several issues (one per failing field); it is skipped once.

## 4. ScoredRow (response)

| Field | Type | Meaning |
|---|---|---|
| input_row | int | joins back to the input |
| rank | int ≥ 1 or null | 1..n over valid rows; null when the batch has one valid row (not ranked) |
| risk_score | number in [0, 1] | the displayed probability, identical to `/score` for the same row (validation-calibrated when a calibrator exists) |
| review_priority | enum `high` / `medium` / `low` | per the rule in §7 |
| top_contributing_features | array (≤ 5) of {feature, contribution, plain_language} | present when requested by `explain`; otherwise empty array |

The raw model score is used server-side for ranking and banding and is not returned (the output
surface stays: score, priority, rank, version, factors, disclaimer).

## 5. BatchResult (response envelope)

| Field | Type | Meaning |
|---|---|---|
| model_version | string | from `models/LATEST` via the loaded bundle |
| operating_point | {primary_k: int, threshold: number} | frozen values read from the bundle at run time |
| batch_limit | int | the enforced limit |
| ranked | boolean | true when ≥ 2 valid rows |
| counts | {received, scored, skipped, high, medium, low} | integers |
| rows | array of ScoredRow | in rank order (or the single row) |
| skipped | array of ValidationIssue | may be empty |
| disclaimer | string | `aml_triage.constants.DISCLAIMER` verbatim |

`additionalProperties: false` at every level; no field named or acting as a decision.

## 6. TriageConfig (GET /triage-config)

| Field | Type |
|---|---|
| model_version | string |
| batch_limit | int (env `AML_BATCH_LIMIT`, default 5000) |
| primary_k | int |
| threshold | number |
| disclaimer | string |

## 7. Ranking and priority rule (batch)

Given valid rows with raw scores `s_i`, steps `t_i`, positions `r_i`, K = `primary_k`,
θ = `threshold`, d = 6 (operating-point decimals):

1. Order by `s` descending, then `t` ascending, then `r` ascending, stable sort (mergesort).
   Rank = position in this order, starting at 1. This equals the pipeline's
   `rank_within_periods` for a single period with `input_row` as `row_index`.
2. `score_d = round(s, d)`.
3. `review_priority = high` if `rank ≤ K` and `score_d ≥ θ`; else `medium` if `score_d ≥ θ`;
   else `low`.
4. If exactly one valid row: `ranked = false`, `rank = null`, `review_priority` from the existing
   score-only `priority()` (high if `score_d ≥ k_score_cutoff`, medium if `≥ θ`, else low).

Consequences the UI states in plain words: at most K rows are `high`; a batch smaller than K has at
most as many `high` rows as above-threshold rows; a routine batch has none.

## 8. UI session state (memory only)

| Key | Content | Lifetime |
|---|---|---|
| client | the TriageClient in use (HTTP by default; in-process in tests) | process |
| config | TriageConfig from the service | until refresh |
| source | `upload` or `manual` | until cleared |
| rows | list of TransactionRow as received (strings normalised, no value changes) | until cleared |
| result | BatchResult | until cleared |
| selected_row | input_row of the row whose explanation is open | until changed |
| explanations | {input_row: factors} fetched on demand | until cleared |

Transitions: `empty → loaded (rows present) → scored (result present) → empty` via "Clear batch";
a page reload returns to `empty`. No transition writes anything outside process memory.

## 9. Exports

See [contracts/export-format.md](contracts/export-format.md). Built from `rows` (inputs) joined to
`result.rows` on `input_row`, plus `result.skipped`.
