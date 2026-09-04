# Data Model: Explainable AML Transaction-Risk Triage

**Date**: 2026-09-04 | **Plan**: [plan.md](plan.md) | **Spec entities**: see spec.md "Key Entities"

This document defines the logical entities the pipeline reads, produces, and persists, with
validation rules drawn from the functional requirements. Physical formats are in
[contracts/artifacts-contract.md](contracts/artifacts-contract.md). Field lists for the raw
dataset are **expected** and confirmed by schema validation (spec V2); engineered field lists are
candidates confirmed by profiling (V10).

## 1. RawTransaction

One row of the source CSV. Unit of analysis.

| Field (expected) | Type | Constraints (enforced by `configs/schema.yaml`) |
|------------------|------|--------------------------------------------------|
| step | int | ≥ 1; non-null |
| type | category | non-null; member of the observed set recorded at profiling |
| amount | float | non-null; ≥ 0 (violations counted as invalid values, not dropped silently) |
| nameOrig | string | non-null; identifier; never a model feature |
| oldbalanceOrg | float | non-null; ≥ 0 expected (negatives counted as invalid) |
| newbalanceOrig | float | non-null; post-transaction state (batch-only availability) |
| nameDest | string | non-null; identifier; never a model feature |
| oldbalanceDest | float | non-null |
| newbalanceDest | float | non-null; post-transaction state (batch-only availability) |
| isFraud | int {0,1} | non-null; target |
| isFlaggedFraud | int {0,1} | non-null; rule comparator only; never a feature |

**Validation**: column presence and dtype coercibility (fail fast, exit code 2); duplicate-row
count recorded; row-level invalid values recorded with counts by type; no row is deleted during
schema validation.

## 2. SplitManifest

Describes the temporal partition. Produced once by `split`; read by everything downstream.

| Field | Type | Rule |
|-------|------|------|
| strategy | enum {temporal, stratified_fallback} | temporal unless FR-041 triggered |
| train_end_step, val_end_step | int | train_end_step < val_end_step < max(step) |
| rows | {train, val, test: int} | sum equals raw rows after documented exclusions |
| positives | {train, val, test: int} | each ≥ `min_positives_per_split` from config |
| step_ranges | {split: [min, max]} | ranges non-overlapping and increasing |
| review_period_steps | int | > 0 |
| excluded_rows | {reason: count} | every exclusion tied to a data-quality decision id |
| config_hash | string | sha256 of `configs/base.yaml` + `configs/schema.yaml` |
| fallback_reason | string or null | required if strategy is stratified_fallback |

**State**: `created` → `frozen` (after M6 `freeze`). Any change to split config after freeze
requires a new config_hash and a new model version.

## 3. FeatureDefinition (feature registry entry, `configs/features.yaml`)

| Field | Type | Rule |
|-------|------|------|
| name | string | unique, snake_case |
| source_columns | list[string] | subset of RawTransaction fields or other feature names |
| transform | string | reference to a function in `aml_triage.features` |
| rationale | string | required, one line (FR-031) |
| available_at_prediction_time | enum {realtime, batch_only} | post-transaction-derived features must be batch_only (R-06) |
| kind | enum {numeric, categorical, flag, aggregate} | aggregates must be causal (FR-032) |
| sets | list[enum {primary, strict_pretx, posttx_ablation, selected, pca_variant}] | `strict_pretx` may not contain batch_only features |
| dictionary_entry | {type, unit, range_or_values, description} | required for `reports/data_dictionary.md` (FR-023) |

Candidate features (confirmed by V10): `type_onehot`, `log_amount`, `amount_bucket`,
`orig_balance_delta`, `dest_balance_delta`, `orig_balance_inconsistent_flag`,
`dest_balance_inconsistent_flag`, `amount_to_orig_balance_ratio`, `orig_zero_balance_flag`,
`dest_zero_balance_flag`, `step_hour_of_day`, `step_day_index`, `orig_prior_txn_count`,
`orig_prior_amount_sum`, `dest_prior_txn_count`, `dest_prior_amount_sum`.

## 4. FittedPipeline

A scikit-learn (or imblearn) `Pipeline` containing preprocessing, optional sampler, optional
selector, optional PCA, and the estimator.

| Field | Rule |
|-------|------|
| fitted_on | must equal `train` split id; recorded by the fit-scope wrapper |
| feature_set | one of the registry sets |
| steps | ordered list; sampler (if any) precedes estimator and is inactive at predict time |
| random_state | equals global seed |
| transforms_fitted_on_rows | count equals SplitManifest.rows.train (or tuning subsample for search only) |

**Invariant (FR-042/043)**: `fit` is never called with validation or test rows; enforced by
`tests/test_leakage.py` via a recording wrapper.

## 5. ModelCandidate

| Field | Type | Rule |
|-------|------|------|
| id | enum {dummy, logreg, balanced_rf, hgb, random_rank, rule_rank} | dummy + ≥3 learners + 2 comparators (FR-050/051) |
| config_path | path | `configs/models/<id>.yaml` (+ `.tuned.yaml` after M6) |
| feature_set | registry set | same set for like-for-like comparisons; ablations labeled |
| imbalance_strategy | enum {class_weight, undersample, none} | recorded per candidate (FR-036) |
| search_space | mapping or null | required for learners in M6 |
| best_params | mapping or null | filled by `tune` |

## 6. EvaluationRun

One evaluation of one candidate on one split.

| Field | Type | Rule |
|-------|------|------|
| candidate_id | ModelCandidate.id | |
| split | enum {val, test} | `test` allowed only when TestAccessRecord permits |
| k_grid | list[int] | includes primary K |
| metrics | MetricSet | see below |
| per_period | list[PeriodResult] | one per review period |
| bootstrap_ci | {pr_auc: [lo, hi], recall_at_k: [lo, hi]} or null | required on test for selected candidates (FR-055) |
| config_hash, model_version, timestamp | string | |

**MetricSet**: pr_auc, roc_auc, precision, recall, f1, fpr, brier, ece, confusion_matrix
(at operating point), accuracy (reported with prevalence, never headline), recall_at_k and
precision_at_k for each K (mean over periods and pooled), prevalence, degenerate_scores (bool;
true when score standard deviation < `evaluation.degenerate_eps` or all scores equal).

**PeriodResult**: period_index, step_range, n_rows, n_positives, k_effective, hits,
recall_at_k (null if n_positives = 0), precision_at_k.

## 7. ReviewQueue

For one review period: transactions ranked for investigator review.

| Field | Rule |
|-------|------|
| period_index, step_range | from SplitManifest.review_period_steps |
| items | ordered by (score desc, step asc, row_index asc) (R-10) |
| item fields | rank, row_index, step, type, risk_score, review_priority ∈ {high, medium, low}, model_version, disclaimer |
| k_effective | min(K, n_rows); shortfall reported when n_rows < K |

**Prohibited fields**: any of allow, block, decision, hold, sar, filing, risk_rating,
customer_rating, fraud_confirmed (enforced by API schema `additionalProperties: false` and the
vocabulary test).

## 8. OperatingPoint

| Field | Rule |
|-------|------|
| primary_k | int; from config after V8 |
| threshold | float in (0,1); chosen on validation by F2 maximization (R-09) |
| calibration | enum {none, isotonic_val}; with decision log |
| chosen_on | must be `val` |
| priority_rule | high = rank ≤ primary_k within the review period; medium = rank > primary_k and score ≥ threshold; low = score < threshold. For single-transaction scoring with no period rank (optional API), high = score ≥ the score of the K-th ranked validation transaction (`k_score_cutoff`, recorded at freeze), medium = score ≥ threshold, low = otherwise |
| frozen_at | timestamp; must precede any TestAccessRecord.first_evaluated_at |

## 9. TestAccessRecord (`data/processed/test_access.json`)

| Field | Rule |
|-------|------|
| config_hash | string |
| frozen_at | timestamp set by `freeze` |
| first_evaluated_at | timestamp set by first `evaluate --split test` |
| reevaluations | list of {timestamp, reason} | non-empty only with `--force-reevaluate --reason` |

**State**: `locked` → `frozen` → `evaluated`. `locked` is the implicit state when `test_access.json` does not exist; `freeze` creates the file in state `frozen`. `evaluate --split test` fails in `locked`.

## 10. SelectionMatrix

Rows = learner candidates; columns = pr_auc, recall_at_k, precision_at_k, calibration
(brier, ece), explainability (qualitative grade + rationale), inference_maintenance_risk
(qualitative), investigator_workload (precision_at_k and FP count per period), verdict. Exactly
one row has verdict `selected`; the matrix must cite validation numbers for selection and test
numbers for reporting.

## 11. ModelBundle (`models/<model_version>/`)

| File | Content |
|------|---------|
| pipeline.joblib | FittedPipeline (gitignored if large; checksum committed) |
| config_snapshot.yaml | merged effective config incl. operating point and feature set |
| metrics.json | EvaluationRun for val and test |
| model_card.md | intended use, non-use, disclaimer, data provenance, metrics, limitations, version, checksum |
| feature_list.json | ordered input feature names the pipeline expects |

`model_version` = `<UTC yyyymmddTHHMMSS>-<git short sha>-<candidate_id>`. `models/LATEST`
contains the selected version id.

## 12. ExplanationSet

| Field | Rule |
|-------|------|
| model_version | must equal models/LATEST at generation |
| global | SHAP summary + mean |SHAP| bar; background = seeded train sample; evaluated on seeded test sample |
| local | ≥ 3 top-K transactions; per-feature contributions; plain-language caption; disclaimer |
| pdp_ice | per top feature: {status ∈ {produced, omitted}, reason, alternative} |
| consistency_notes | discussion against EDA (FR-063) |

## 13. SensitiveAttributeAvailabilityRecord

| Field | Rule |
|-------|------|
| attributes_checked | fixed list: age, gender, ethnicity, nationality, socioeconomic_status, plus proxy scan of column names |
| per_attribute | {present: bool, evidence: string} |
| any_valid_label | bool |
| decided_on | date |

The fairness report branches on `any_valid_label`: true → DemographicFairnessResult;
false → explicit non-measurability statement + OperationalSliceResult.

## 14. OperationalSliceResult

| Field | Rule |
|-------|------|
| label | literal `"operational error-slice analysis"` (FR-073); never a fairness term |
| slice_dimension | enum {type, amount_band, orig_balance_band, step_band} |
| per_slice | {n, prevalence, recall_at_k, precision_at_k, fpr, fnr, brier} |
| notes | interpretation limited to operational error behavior |

## 15. DemographicFairnessResult (only if any_valid_label)

| Field | Rule |
|-------|------|
| group_attribute | from availability record |
| metrics | demographic_parity_difference, equalized_odds_difference, disparate_impact_ratio |
| mitigations | list; concrete and feasible (FR-076) |

## 16. Disclaimer

Single constant `aml_triage.constants.DISCLAIMER`. Required, verbatim, on: every report table
footer, every figure caption block, ReviewQueue items, API responses, notebook headers, deck
title and closing slides, model card.

## Relationships

```
RawTransaction ──split──▶ SplitManifest ──▶ {train, val, test}
FeatureDefinition[] ──build──▶ FittedPipeline (fit: train only)
ModelCandidate + FittedPipeline ──evaluate──▶ EvaluationRun (val) ──tune/choose──▶ OperatingPoint
OperatingPoint + TestAccessRecord(frozen) ──evaluate──▶ EvaluationRun (test) ──▶ SelectionMatrix ──▶ ModelBundle
ModelBundle ──▶ ReviewQueue, ExplanationSet
SensitiveAttributeAvailabilityRecord ──▶ (DemographicFairnessResult | OperationalSliceResult)
```

## Glossary of rule-related terms

| Term | Meaning | Use it for |
|------|---------|------------|
| `isFlaggedFraud` | The dataset's rule-flag column (expected; V2/V6 confirm) | Column name in schema, code, and data dictionary |
| rule comparator (`rule_rank`) | Ranking that places flagged rows first, then amount descending; falls back to a documented amount rule if the column is absent | Tables, report prose, `ModelCandidate.id` |
| random comparator (`random_rank`) | Seeded random ranking; the primary null hypothesis | Tables and report prose |
| dummy baseline (`dummy`) | Prior-rate classifier with constant scores; ranks as chronological order under tie-break | Tables (labeled "chronological order") |

Avoid "rule baseline" and "rule flag" as standalone terms; use the forms above.
