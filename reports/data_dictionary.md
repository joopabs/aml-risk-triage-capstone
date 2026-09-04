# Data Dictionary

## Conventions

`availability`: `realtime` = known when the transaction is observed; `batch_only` = known in end-of-period batch triage (post-transaction state, research R-06); `label` = target, never an input. Identifiers are never model features (FR-033). Observed ranges come from `reports/data_quality.json`; `[PROFILE]` means profiling has not run yet.

## Raw variables

| variable | type | unit | range / allowed values | role | prediction-time availability | description |
|---|---|---|---|---|---|---|
| step | int32 | hours since simulation start (expected; V8 confirms) | [PROFILE] | time_index | realtime | Simulation time step; one unit is expected to represent one hour. |
| type | category | category | [PROFILE] | feature | realtime | Transaction type (expected values include CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER; V2 confirms). |
| amount | float32 | currency units (simulated) | [PROFILE] | feature | realtime | Transaction amount in the simulator's currency units. |
| nameOrig | string | identifier | [PROFILE] | identifier | realtime | Origin account identifier. Never a model feature; used only for causal aggregates. |
| oldbalanceOrg | float32 | currency units (simulated) | [PROFILE] | feature | realtime | Origin account balance before the transaction. |
| newbalanceOrig | float32 | currency units (simulated) | [PROFILE] | feature | batch_only | Origin account balance after the transaction (post-transaction state). |
| nameDest | string | identifier | [PROFILE] | identifier | realtime | Destination account identifier. Never a model feature; used only for causal aggregates. |
| oldbalanceDest | float32 | currency units (simulated) | [PROFILE] | feature | realtime | Destination account balance before the transaction. |
| newbalanceDest | float32 | currency units (simulated) | [PROFILE] | feature | batch_only | Destination account balance after the transaction (post-transaction state). |
| isFraud | int8 | binary flag | 0, 1 | target | label | Simulated fraud label; 1 = simulated fraud, 0 = simulated normal transaction. |
| isFlaggedFraud | int8 | binary flag | 0, 1 | rule_comparator | batch_only | Simulator rule flag. Never a model feature; defines the rule comparator ranking. |

## Engineered features

_No feature registry yet (configs/features.yaml is created in Milestone 3, task T028)._


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
