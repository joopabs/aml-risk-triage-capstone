# Model Card: hgb [primary] 20260904T225142-0dc8f82-hgb

## Model Details

Version `20260904T225142-0dc8f82-hgb`; candidate `hgb` on feature set `primary`; trained on 5,987,417 training rows (4,589 positives); tuned parameters used: True. Pipeline checksum in `pipeline.sha256`.

## Intended Use

Educational decision-support prototype that ranks synthetic PaySim transactions so a fixed daily investigator capacity is spent on the transactions most worth a human look. Outputs: risk score, review priority (high/medium/low), model version, disclaimer.

## Non-Use

No automatic blocking, account closure, customer risk rating, regulatory reporting, or AML determination. Not validated for real customer data; a governance-controlled validation and fairness audit would be required before any real use.

## Data

PaySim is synthetic mobile-money transaction data. It is not real SME, corporate, or Philippine banking data. Source and license recorded in `data/README.md` and `configs/data_source.yaml` (CC BY-SA 4.0). Temporal split: train steps 1–408, validation 409–552, test 553–743.

## Metrics

| split | PR-AUC | ROC-AUC | Recall@200 mean | Recall@200 pooled | Precision@200 | Brier | ECE |
|---|---|---|---|---|---|---|---|
| validation | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0000 | 0.0000 |
| test | 1.0000 | 1.0000 | 0.7568 | 0.7547 | 1.0000 | 0.0000 | 0.0000 |

Test 95% bootstrap CIs (200 resamples): PR-AUC [1.0, 1.0], pooled Recall@200 [0.7252291320132905, 0.7866466912874829].

## Operating Point

Chosen on validation only. Threshold 0.971931 (rule f2_max_on_val_raw_scores); priority rule {'high': 'rank_le_k', 'medium': 'above_threshold', 'low': 'below_threshold'}; K-th score cutoff 0.999977; calibration `isotonic_val` (applied: True). Test metrics at the operating point: precision 1.0000, recall 0.9976, FPR 0.000000, confusion {'fn': 5, 'fp': 0, 'tn': 192015, 'tp': 2115}.

## Explainability Summary

See `reports/explainability.md` (Milestone 7): SHAP global and local explanations, PDP/ICE where valid.

## Limitations

Near-perfect separability is a property of the PaySim generator, not evidence of AML capability. Validation and test prevalence exceed training prevalence by an order of magnitude (simulator injects positives at a constant rate). Several strong features are simulator artifacts (balance bookkeeping, zero amounts). Results cannot establish real-world detection effectiveness, fairness, or regulatory suitability.

## Fairness Statement

Sensitive-attribute availability is recorded in Milestone 7 (`reports/fairness_availability.json`); PaySim carries no demographic attributes, so only an operational error-slice analysis is possible.

## Version and Checksums

`models/LATEST` → `20260904T225142-0dc8f82-hgb`; `pipeline.sha256` holds the SHA-256 of `pipeline.joblib` (the joblib file is regenerated with `make pipeline` and is not committed).


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
