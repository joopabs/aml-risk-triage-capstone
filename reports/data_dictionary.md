# Data Dictionary

## Conventions

`availability`: `realtime` = known when the transaction is observed; `batch_only` = known in end-of-period batch triage (post-transaction state, research R-06); `label` = target, never an input. Identifiers are never model features (FR-033). Observed ranges come from `reports/data_quality.json`; `[PROFILE]` means profiling has not run yet.

## Raw variables

| variable | type | unit | range / allowed values | role | prediction-time availability | description |
|---|---|---|---|---|---|---|
| step | int32 | hours since simulation start (expected; V8 confirms) | 1 – 743 | time_index | realtime | Simulation time step; one unit is expected to represent one hour. |
| type | category | category | CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER | feature | realtime | Transaction type (expected values include CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER; V2 confirms). |
| amount | float32 | currency units (simulated) | 0.00 – 92,445,520.00 | feature | realtime | Transaction amount in the simulator's currency units. |
| nameOrig | string | identifier | 6,353,307 unique | identifier | realtime | Origin account identifier. Never a model feature; used only for causal aggregates. |
| oldbalanceOrg | float32 | currency units (simulated) | 0.00 – 59,585,040.00 | feature | realtime | Origin account balance before the transaction. |
| newbalanceOrig | float32 | currency units (simulated) | 0.00 – 49,585,040.00 | feature | batch_only | Origin account balance after the transaction (post-transaction state). |
| nameDest | string | identifier | 2,722,362 unique | identifier | realtime | Destination account identifier. Never a model feature; used only for causal aggregates. |
| oldbalanceDest | float32 | currency units (simulated) | 0.00 – 356,015,904.00 | feature | realtime | Destination account balance before the transaction. |
| newbalanceDest | float32 | currency units (simulated) | 0.00 – 356,179,264.00 | feature | batch_only | Destination account balance after the transaction (post-transaction state). |
| isFraud | int8 | binary flag | 0, 1 | target | label | Simulated fraud label; 1 = simulated fraud, 0 = simulated normal transaction. |
| isFlaggedFraud | int8 | binary flag | 0, 1 | rule_comparator | batch_only | Simulator rule flag. Never a model feature; defines the rule comparator ranking. |

## Engineered features

| variable | type | unit | range / allowed values | role | prediction-time availability | description |
|---|---|---|---|---|---|---|
| type_onehot | one-hot (5 columns) | indicator | 0/1 per observed type | categorical | realtime | One column per transaction type observed in training; unknown types map to all zeros. Rationale: Simulated fraud occurs only in TRANSFER and CASH_OUT (DQ-09); type is the first-order signal. |
| log_amount | float | log(currency units + 1) | >= 0 | numeric | realtime | log1p(amount). Rationale: Amounts are heavy-tailed (DQ-07); log scale stabilises linear models and keeps tree splits interpretable. |
| amount_bucket | int | bucket index | 0..n_bins-1 (n_bins=10) | numeric | realtime | Amount decile bucket; edges fitted on the training split only. Rationale: Quantile buckets fitted on training data give a monotone, outlier-robust view of amount for slice analysis and linear models. |
| log_oldbalance_org | float | log(currency units + 1) | >= 0 | numeric | realtime | log1p(oldbalanceOrg). Rationale: Origin balance before the transaction is heavy-tailed with a mass at zero (DQ-07); log scale plus a zero flag captures both. |
| log_oldbalance_dest | float | log(currency units + 1) | >= 0 | numeric | realtime | log1p(oldbalanceDest). Rationale: Destination balance before the transaction; merchants carry zero (DQ-06), customers vary widely. |
| amount_to_orig_balance_ratio | float | ratio | >= 0 | numeric | realtime | amount / (oldbalanceOrg + 1). Rationale: Emptying an account (ratio near 1) is a classic mule-account pattern; the +1 guard handles zero balances. |
| orig_zero_balance_flag | int | indicator | 0/1 | flag | realtime | oldbalanceOrg == 0. Rationale: 2.1M rows start from a zero origin balance (DQ-07); the flag separates this mass from the continuous scale. |
| dest_zero_balance_flag | int | indicator | 0/1 | flag | realtime | oldbalanceDest == 0. Rationale: Zero destination balance before the transaction marks merchants and fresh accounts (DQ-06). |
| zero_amount_flag | int | indicator | 0/1 | flag | realtime | amount == 0. Simulator artifact (DQ-03). Rationale: All 16 zero-amount rows are positives (DQ-03); kept as a feature but reported as a simulator artifact, never as transferable signal. |
| dest_is_merchant | int | indicator | 0/1 | flag | realtime | nameDest starts with 'M'. Derived account type; the identifier itself is dropped (FR-033). Rationale: Merchant destinations (identifier prefix M) receive only PAYMENT and carry no positives or balance state (DQ-06); this is account type, not identity. |
| step_hour_of_day | int | hour | 0..23 | numeric | realtime | (step - 1) mod 24. Rationale: Hourly position within the simulated day may carry volume seasonality; cyclic and in-range for every split. |
| step_day_index | int | day | 0..30 | numeric | realtime | (step - 1) // 24. Excluded from every modeling set. Rationale: Diagnostic only. Under a temporal split the test days are out of the training range, so using it would encode regime rather than behaviour (DQ-10). |
| orig_balance_delta | float | currency units | any | numeric | batch_only | oldbalanceOrg - newbalanceOrig. Rationale: Posted change in origin balance; in batch triage the posted state is available and its mismatch with amount is informative (DQ-05). |
| dest_balance_delta | float | currency units | any | numeric | batch_only | newbalanceDest - oldbalanceDest. Rationale: Posted change in destination balance (DQ-06). |
| orig_balance_inconsistent_flag | int | indicator | 0/1 | flag | batch_only | |newbalanceOrig - expected| > 0.01 where expected = old + amount for CASH_IN, old - amount otherwise. Rationale: Direction-aware arithmetic gap on the origin side is inconsistent for most CASH_OUT/TRANSFER rows (DQ-05); a simulator behaviour that correlates with the label. |
| dest_balance_inconsistent_flag | int | indicator | 0/1 | flag | batch_only | |newbalanceDest - oldbalanceDest - amount| > 0.01. Rationale: Destination arithmetic gap (DQ-06); always inconsistent for merchant destinations. |
| orig_zero_after_flag | int | indicator | 0/1 | flag | batch_only | oldbalanceOrg > 0 and newbalanceOrig == 0. Rationale: Account emptied to exactly zero after the transaction (DQ-05); a strong mule pattern in the simulator. |
| orig_prior_txn_count | int | count | >= 0 | aggregate | realtime | Count of earlier transactions with the same nameOrig (strictly earlier step, or earlier file position within the same step). Rationale: Number of strictly earlier transactions by the same origin; expected near zero because origins rarely repeat (DQ-11), kept to let V10 confirm. |
| orig_prior_amount_sum | float | currency units | >= 0 | aggregate | realtime | Sum of amount over earlier transactions with the same nameOrig. Rationale: Cumulative earlier outflow by the same origin (DQ-11). |
| dest_prior_txn_count | int | count | >= 0 | aggregate | realtime | Count of earlier transactions with the same nameDest. Rationale: Destinations repeat (16.9% appear more than once, max 113; DQ-11); accumulation into one destination is a laundering-style pattern. |
| dest_prior_amount_sum | float | currency units | >= 0 | aggregate | realtime | Sum of amount over earlier transactions with the same nameDest. Rationale: Cumulative earlier inflow to the same destination (DQ-11). |


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
