# Feature Selection

## Scope

Feature set `primary`, training split only, seeded stratified subsample of 1,000,000 rows with 766 positives (research R-08). Fit scope: MI ['train'], L1 ['train'].

## Before

24 columns: `type_CASH_IN`, `type_CASH_OUT`, `type_DEBIT`, `type_PAYMENT`, `type_TRANSFER`, `amount_bucket`, `log_amount`, `log_oldbalance_org`, `log_oldbalance_dest`, `amount_to_orig_balance_ratio`, `orig_zero_balance_flag`, `dest_zero_balance_flag`, `zero_amount_flag`, `dest_is_merchant`, `step_hour_of_day`, `orig_balance_delta`, `dest_balance_delta`, `orig_balance_inconsistent_flag`, `dest_balance_inconsistent_flag`, `orig_zero_after_flag`, `orig_prior_txn_count`, `orig_prior_amount_sum`, `dest_prior_txn_count`, `dest_prior_amount_sum`

Constant columns (no information on the subsample): none

## Filter method: mutual information (top 12)

| column | MI score | selected |
|---|---|---|
| dest_balance_inconsistent_flag | 0.1872 | yes |
| orig_balance_inconsistent_flag | 0.1831 | yes |
| dest_zero_balance_flag | 0.1031 | yes |
| type_CASH_OUT | 0.0760 | yes |
| dest_is_merchant | 0.0711 | yes |
| type_PAYMENT | 0.0708 | yes |
| orig_zero_balance_flag | 0.0690 | yes |
| orig_zero_after_flag | 0.0379 | yes |
| type_CASH_IN | 0.0319 | yes |
| amount_bucket | 0.0247 | yes |
| step_hour_of_day | 0.0189 | yes |
| amount_to_orig_balance_ratio | 0.0059 | yes |
| type_TRANSFER | 0.0048 |  |
| orig_balance_delta | 0.0032 |  |
| dest_prior_txn_count | 0.0028 |  |
| log_amount | 0.0008 |  |
| log_oldbalance_org | 0.0008 |  |
| dest_balance_delta | 0.0004 |  |
| type_DEBIT | 0.0001 |  |
| log_oldbalance_dest | 0.0001 |  |
| dest_prior_amount_sum | 0.0001 |  |
| orig_prior_txn_count | 0.0000 |  |
| orig_prior_amount_sum | 0.0000 |  |
| zero_amount_flag | 0.0000 |  |

## Embedded method: L1 logistic regression (C = 0.1, standardised inputs, balanced class weight)

| column | coefficient | non-zero |
|---|---|---|
| orig_zero_balance_flag | 8.8216 | yes |
| orig_balance_inconsistent_flag | -5.6202 | yes |
| orig_zero_after_flag | 5.2283 | yes |
| log_oldbalance_dest | -4.3553 | yes |
| type_CASH_OUT | 4.0187 | yes |
| dest_balance_delta | -3.5508 | yes |
| log_oldbalance_org | 3.2417 | yes |
| type_TRANSFER | 2.8905 | yes |
| dest_zero_balance_flag | -2.7713 | yes |
| type_CASH_IN | -2.6181 | yes |
| amount_to_orig_balance_ratio | 2.2877 | yes |
| step_hour_of_day | -1.0616 | yes |
| log_amount | 1.0095 | yes |
| dest_balance_inconsistent_flag | 0.7384 | yes |
| amount_bucket | -0.6153 | yes |
| orig_balance_delta | 0.5111 | yes |
| dest_prior_txn_count | -0.1582 | yes |
| orig_prior_txn_count | -0.0329 | yes |
| zero_amount_flag | 0.0096 | yes |
| dest_is_merchant | 0.0000 |  |
| dest_prior_amount_sum | 0.0000 |  |
| orig_prior_amount_sum | 0.0000 |  |
| type_DEBIT | 0.0000 |  |
| type_PAYMENT | 0.0000 |  |

## After

Intersection (10): `type_CASH_IN`, `type_CASH_OUT`, `amount_bucket`, `amount_to_orig_balance_ratio`, `orig_zero_balance_flag`, `dest_zero_balance_flag`, `step_hour_of_day`, `orig_balance_inconsistent_flag`, `dest_balance_inconsistent_flag`, `orig_zero_after_flag`

Combine rule `intersection_or_union_if_lt` → **intersection (10 >= min_size 6)**.

**Selected columns (10)**: `type_CASH_IN`, `type_CASH_OUT`, `amount_bucket`, `amount_to_orig_balance_ratio`, `orig_zero_balance_flag`, `dest_zero_balance_flag`, `step_hour_of_day`, `orig_balance_inconsistent_flag`, `dest_balance_inconsistent_flag`, `orig_zero_after_flag`

**Dropped columns (14)**: `type_DEBIT`, `type_PAYMENT`, `type_TRANSFER`, `log_amount`, `log_oldbalance_org`, `log_oldbalance_dest`, `zero_amount_flag`, `dest_is_merchant`, `orig_balance_delta`, `dest_balance_delta`, `orig_prior_txn_count`, `orig_prior_amount_sum`, `dest_prior_txn_count`, `dest_prior_amount_sum`

**Registry `selected` set (9 features)**: `type_onehot`, `amount_bucket`, `amount_to_orig_balance_ratio`, `orig_zero_balance_flag`, `dest_zero_balance_flag`, `step_hour_of_day`, `orig_balance_inconsistent_flag`, `dest_balance_inconsistent_flag`, `orig_zero_after_flag`

## Why this combined set (task T041, written 2026-09-05 after reviewing the tables above)

Both methods were fitted on the same seeded stratified subsample of 1,000,000 training rows
(about 770 positives). Their intersection has 10 columns, above the `min_size` of 6, so the
intersection rule applied and no union fallback was needed. At registry level that is 9 features,
because `type_onehot` is kept whole: a one-hot block cannot be partially selected, so the `selected`
matrix carries all five type columns (13 columns in total).

The two methods agree on the account-state signals seen in EDA: `orig_zero_balance_flag`,
`orig_zero_after_flag`, `amount_to_orig_balance_ratio`, `dest_zero_balance_flag`, the two
balance-inconsistency flags, `amount_bucket`, `step_hour_of_day`, and the CASH_IN / CASH_OUT type
indicators.

Two readings of the tables matter for later milestones:

- **Mutual information ranks the two balance-inconsistency flags first (0.187 and 0.183)**, ahead of
  transaction type. Those flags are simulator artifacts (DQ-05, eda_08). The `selected` set therefore
  contains four of the five batch-only features and is not a prediction-time-safe set. It is a
  statistical selection, not a deployment recommendation; `strict_pretx` remains the honest
  comparison in Milestone 5.
- **L1 coefficient signs are not individually interpretable.** `orig_zero_balance_flag` receives the
  largest coefficient (+8.8) although EDA shows zero-balance origins almost never positive. The
  feature is strongly collinear with `amount_to_orig_balance_ratio` (ρ = 0.81) and
  `log_oldbalance_org` (ρ = −0.83), so the signs offset each other. Only non-zero magnitude was used
  for selection.

## Features dropped and why

| Dropped column | Reason from the tables |
|---|---|
| `log_amount` | Redundant with `amount_bucket` (ρ = 0.99); MI prefers the training-fitted deciles (0.025 vs 0.001). L1 kept it, so it fails the intersection only. |
| `log_oldbalance_org`, `log_oldbalance_dest` | Large L1 coefficients but MI below 0.001; their information is carried by the zero-balance flags and the ratio. |
| `dest_is_merchant` | MI 0.071 (informative) but L1 coefficient exactly zero because `type_PAYMENT` and `dest_zero_balance_flag` (ρ = 0.81) encode the same rows. |
| `zero_amount_flag` | MI 0.000: only 4 training rows carry the flag, too few for a density estimate; L1 coefficient 0.01. Kept in the `primary` set as a documented artifact (DQ-03). |
| `orig_prior_txn_count`, `orig_prior_amount_sum` | MI 0.000 and near-zero coefficients: origins do not repeat (DQ-11, eda_07). Confirms the EDA recommendation to drop. |
| `dest_prior_txn_count`, `dest_prior_amount_sum` | Weak on both methods (MI ≤ 0.003; L1 ≤ 0.16 in magnitude). |
| `orig_balance_delta`, `dest_balance_delta` | Their information is captured by the inconsistency and zero-after flags; MI ≤ 0.003. |
| `type_TRANSFER`, `type_PAYMENT`, `type_DEBIT` (columns) | Dropped at column level (one-hot redundancy: with two type columns present the others are implied) but retained in the matrix because `type_onehot` is one registry feature. |

## Caveats

- MI was estimated on a subsample with about 770 positives; the ranking of features below 0.01 is
  noisy and should not be over-read.
- The `selected` set will be evaluated as one candidate feature set in Milestone 5 alongside
  `primary`, `strict_pretx` and `posttx_ablation`; selection here makes no claim about model
  performance.
- Fit scope was training-only for both selectors (`fitted_on: ['train']`), enforced by the
  fit-scope recorder and `tests/test_features.py`.


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
