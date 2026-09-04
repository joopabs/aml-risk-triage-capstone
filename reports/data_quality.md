# Data Quality Report

## Scope

Source: `data/raw/PS_20174392719_1491204439457_log.csv`. Rows: 6,362,620. Columns: 11. All figures below are aggregates; no row-level data is shown.

## Columns and nulls

| column | dtype | nulls |
|---|---|---|
| step | int32 | 0 |
| type | category | 0 |
| amount | float32 | 0 |
| nameOrig | string | 0 |
| oldbalanceOrg | float32 | 0 |
| newbalanceOrig | float32 | 0 |
| nameDest | string | 0 |
| oldbalanceDest | float32 | 0 |
| newbalanceDest | float32 | 0 |
| isFraud | int8 | 0 |
| isFlaggedFraud | int8 | 0 |

## Duplicates

| kind | count |
|---|---|
| exact duplicate rows | 0 |
| near-duplicates ignoring identifiers | 543 |

## Numeric summary and outliers (IQR rule)

| column | min | p50 | p95 | p99 | p99.9 | max | zeros | negatives | IQR outliers |
|---|---|---|---|---|---|---|---|---|---|
| amount | 0.0000 | 74,871.94 | 518,634.19 | 1,615,979.50 | 8,956,797.63 | 92,445,520.00 | 16 | 0 | 338,078 |
| oldbalanceOrg | 0.0000 | 14,208.00 | 5,823,702.10 | 16,027,256.35 | 26,825,930.48 | 59,585,040.00 | 2,102,449 | 0 | 1,112,507 |
| newbalanceOrig | 0.0000 | 0.0000 | 5,980,262.37 | 16,176,160.39 | 26,971,659.15 | 49,585,040.00 | 3,609,566 | 0 | 1,053,391 |
| oldbalanceDest | 0.0000 | 132,705.66 | 5,147,229.70 | 12,371,819.49 | 34,392,787.85 | 356,015,904.00 | 2,704,388 | 0 | 786,135 |
| newbalanceDest | 0.0000 | 214,661.45 | 5,515,715.97 | 13,137,866.93 | 39,531,570.22 | 356,179,264.00 | 2,439,433 | 0 | 738,527 |

## Amount quantiles by transaction type

| type | p50 | p95 | p99 | p99.9 | max |
|---|---|---|---|---|---|
| CASH_IN | 143,427.71 | 412,005.12 | 550,870.85 | 727,791.33 | 1,915,267.88 |
| CASH_OUT | 147,072.19 | 427,877.16 | 579,654.09 | 864,676.47 | 10,000,000.00 |
| DEBIT | 3,048.99 | 14,795.35 | 50,817.98 | 179,208.45 | 569,077.50 |
| PAYMENT | 9,482.19 | 37,835.66 | 59,500.11 | 89,701.44 | 238,637.98 |
| TRANSFER | 486,308.38 | 2,674,586.95 | 10,000,000.00 | 24,840,512.69 | 92,445,520.00 |

## Invalid values

| check | count |
|---|---|
| zero amount | 16 |
| negative amount | 0 |
| negative oldbalanceOrg | 0 |
| negative newbalanceOrig | 0 |
| negative oldbalanceDest | 0 |
| negative newbalanceDest | 0 |
| origin balance arithmetic inconsistent (tol 0.01) | 3,953,846 |
| destination balance arithmetic inconsistent (tol 0.01) | 5,229,368 |

## Balance arithmetic by type

| type | n | orig inconsistent | rate | dest inconsistent | rate | orig zero after | dest both zero |
|---|---|---|---|---|---|---|---|
| CASH_IN | 1,399,284 | 234,237 | 0.1674 | 1,399,284 | 1.0000 | 0 | 160,005 |
| CASH_OUT | 2,237,500 | 2,007,949 | 0.8974 | 1,324,750 | 0.5921 | 959,412 | 1,608 |
| DEBIT | 41,432 | 12,660 | 0.3056 | 23,467 | 0.5664 | 5,628 | 0 |
| PAYMENT | 2,151,495 | 1,187,615 | 0.5520 | 2,151,495 | 1.0000 | 326,879 | 2,151,495 |
| TRANSFER | 532,909 | 511,385 | 0.9596 | 330,372 | 0.6199 | 228,662 | 4,174 |

## Class imbalance

| metric | value |
|---|---|
| positives (simulated fraud) | 8,213 |
| negatives | 6,354,407 |
| prevalence | 0.0013 |
| negatives per positive | 773.7011 |

| type | n | positives | rate |
|---|---|---|---|
| CASH_IN | 1,399,284 | 0 | 0.0000 |
| CASH_OUT | 2,237,500 | 4,116 | 0.0018 |
| DEBIT | 41,432 | 0 | 0.0000 |
| PAYMENT | 2,151,495 | 0 | 0.0000 |
| TRANSFER | 532,909 | 4,097 | 0.0077 |

## Time steps

| metric | value |
|---|---|
| steps observed | 743 |
| step range | 1–743 |
| transactions per step (min / median / max) | 2 / 529 / 51,352 |
| positives per step (min / median / max) | 0 / 10 / 40 |
| steps with zero positives | 2 |
| first / last step with a positive | 1 / 743 |

Per-step counts are in `data_quality.json` under `steps.transactions_by_step` and `steps.cumulative_positives_by_step` (used to choose split bounds, V9).

## Identifiers

| column | unique | share appearing >1 | max occurrences |
|---|---|---|---|
| nameOrig | 6,353,307 | 0.0015 | 3 |
| nameDest | 2,722,362 | 0.1688 | 113 |

## Rule flag column

| column | flagged | rate | flagged and positive | precision as rule | recall as rule |
|---|---|---|---|---|---|
| isFlaggedFraud | 16 | 0.0000 | 16 | 1.0000 | 0.0019 |

## Sensitive-attribute pre-scan

Column names checked against: age, gender, sex, ethnicity, race, nationality, income, socioeconomic, region, zip, postcode, birth, religion, marital.

No column name matches a sensitive-attribute pattern. The formal availability record is produced in Milestone 7 (FR-070).

## Findings and handling decisions

Written after reviewing the generated tables (task T022, 2026-09-05). Every number below is copied
from `reports/data_quality.json`. Decisions are one of keep, correct, flag as feature, exclude.

| ID | Finding (from the tables above) | Decision | Justification |
|----|--------------------------------|----------|---------------|
| DQ-01 | 6,362,620 rows, 11 columns, 0 nulls in every column. | keep | Nothing to impute; the imputation step in the pipeline is a no-op guard only. |
| DQ-02 | 0 exact duplicate rows; 543 near-duplicate pairs when identifiers are ignored (1,081 rows, 27 of them positives). | keep | Identical amounts and balances with different accounts are distinct transactions in a simulator with coarse value grids; dropping them would delete real positives. |
| DQ-03 | 16 zero-amount rows, all CASH_OUT, and all 16 are positives. | flag as feature, treat as artifact | A zero-amount transaction has no economic meaning; a perfect label correlation on 16 rows is a simulator artifact. `zero_amount_flag` is kept as a feature but the report must state that it contributes leakage-like lift, and the strict feature set is evaluated with and without it (research R-06). |
| DQ-04 | No negative amounts or balances. | keep | Hard minimums hold; soft minimums record zero violations. |
| DQ-05 | Origin balance arithmetic (direction-aware, tolerance 0.01) is inconsistent for 89.7% of CASH_OUT, 96.0% of TRANSFER, 55.2% of PAYMENT, 30.6% of DEBIT and 16.7% of CASH_IN rows. | flag as feature | Inconsistency is simulator behavior, not an error to correct. `orig_balance_inconsistent_flag` and the signed gap become batch-only features; their importance is reported as artifact evidence. |
| DQ-06 | Destination balance arithmetic is inconsistent for 100% of PAYMENT and CASH_IN rows and 59–62% of CASH_OUT/TRANSFER rows. All 2,151,495 PAYMENT destinations are merchants (identifier prefix M), all with both destination balances equal to zero, and none of them is a positive. | flag as feature | Merchants carry no balance state in PaySim. `dest_is_merchant` (derived from the identifier prefix, not the identifier itself) and `dest_balance_inconsistent_flag` are batch-only features. FR-033 is respected because account identity is never used. |
| DQ-07 | Heavy tails: amount p50 74,872 vs max 92,445,520; 338,078 IQR outliers; TRANSFER p99 is exactly 10,000,000. 5,650 rows at or above 10,000,000 contain 287 positives and only 3 rule flags. | keep, transform | Positives live in the tails, so no removal. Use `log1p(amount)` and training-fitted amount buckets; report per-type quantiles. |
| DQ-08 | 8,213 positives, prevalence 0.129%, 774 negatives per positive. | keep, handle in training | Class weighting or in-fold undersampling only (FR-036); PR-AUC primary; accuracy never a headline (FR-007). |
| DQ-09 | Positives occur only in CASH_OUT (4,116) and TRANSFER (4,097). CASH_IN, DEBIT and PAYMENT have zero positives across 3.59 million rows. | keep all types | The model must score every type; type is a first-order feature. Ablations on TRANSFER/CASH_OUT only are reported as a sensitivity check, not as the primary result. |
| DQ-10 | Steps 1–743 are contiguous. Transaction volume is highly non-stationary: 574,255 transactions in day 1 and 455,238 in day 2, then 1,070 in day 3; days 6–17 carry roughly 350,000–450,000 each; days 18–31 carry 272 to 57,853. Positives are almost constant at 216–320 per day regardless of volume; day 31 (steps 721–743) has 272 transactions, all positive. | keep, constrain split design | Simulated fraud is injected at a near-constant rate independent of volume, so prevalence in late steps is orders of magnitude above early steps. The temporal split (T025) must be chosen so validation and test periods contain enough transactions per review period for Recall@K to mean anything, and the report must present validation-vs-test shift explicitly. |
| DQ-11 | Origin identifiers are almost never reused (6,353,307 unique; 0.15% appear more than once; max 3). Destination identifiers are reused (2,722,362 unique; 16.9% appear more than once; max 113). | keep, guide features | Prior-transaction aggregates per origin are expected to be uninformative; destination aggregates are the causal-aggregate candidates (V10 decides). Identifiers themselves are dropped after aggregation. |
| DQ-12 | Rule flag `isFlaggedFraud` fires 16 times, all on positives: precision 1.000, recall 0.0019. | keep as comparator only | Too sparse to rank a queue on its own; the rule comparator ranks flagged rows first then by amount descending (research R-10). Never a model feature. |
| DQ-13 | No column name matches a sensitive-attribute pattern. | record | The formal availability record (FR-070) is produced in Milestone 7; the expected path is the operational error-slice analysis. |

## Source-data limitations

- **Synthetic origin.** PaySim is generated by an agent-based simulator seeded with aggregate
  statistics from a mobile-money service. Nothing here is real SME, corporate, or Philippine banking
  data, and no result can establish real-world detection effectiveness, fairness, or regulatory
  suitability.
- **Constant fraud injection (DQ-10).** Positives arrive at a near-constant daily rate while
  legitimate volume swings by three orders of magnitude. Late-period prevalence is therefore
  artificially high, and any temporal test split inherits that shift. This is the single largest
  threat to interpreting Recall@K as an operational figure.
- **Label-correlated artifacts (DQ-03, DQ-05, DQ-06).** Zero amounts, balance-arithmetic gaps and
  zero-balance destinations correlate with the label because of how the simulator writes state,
  not because of transferable behavior. Features built from them are kept for the batch-triage
  framing but must be reported as artifact-driven lift, with a strict feature set as the
  comparison.
- **Merchant state is absent (DQ-06).** Merchant destinations have no balances, so destination
  features are uninformative for PAYMENT and only meaningful for customer-to-customer types.
- **Two positive types only (DQ-09).** Results say nothing about detecting simulated fraud in
  CASH_IN, DEBIT or PAYMENT, because none exists in the data.
- **Coarse time index.** `step` is an hourly index with no calendar, weekday or intraday
  semantics beyond position; period boundaries for Recall@K are an analytical convention
  (24 steps), not an observed business day.
- **No demographics (DQ-13).** Demographic fairness cannot be measured; only operational
  error slices can be reported, and they must not be described as fairness across protected groups.


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
