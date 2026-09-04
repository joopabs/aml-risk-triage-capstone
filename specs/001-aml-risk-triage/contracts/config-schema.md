# Config Schema (`configs/*.yaml`)

Loaded and validated by `aml_triage.config` (pydantic). Unknown keys are errors. Nulls marked
"set after Vn" must be filled before the dependent command runs; the loader rejects nulls for
commands that need them (exit 2).

## configs/base.yaml
```yaml
seed: 42
paths:
  raw_csv: data/raw/<filename>        # from data_source.yaml
  processed_dir: data/processed
  models_dir: models
  reports_dir: reports
split:
  strategy: temporal                  # temporal | stratified_fallback
  train_end_step: null                # set after V9
  val_end_step: null                  # set after V9
  min_positives_per_split: null       # set after V4
  fallback_reason: null
review:
  review_period_steps: null           # set after V8 (expected 24)
  primary_k: null                     # set after V8
  k_grid: []                          # e.g. several K values around primary
  tie_break: [score_desc, step_asc, row_index_asc]
features:
  registry: configs/features.yaml
  default_set: primary
  ablation_sets: [strict_pretx, posttx_ablation]
selection:
  mi_k: null                          # set after V10
  l1_c: null
  combine_rule: intersection_or_union_if_lt   # with min_size
  min_size: null
pca:
  n_components: null                  # or variance target
  role: diagnostic_and_visualization
tuning:
  tune_sample_rows: null              # set after V3
  n_iter: 30
  cv_folds: 3                         # stratified within train subsample only
  scoring: average_precision
calibration:
  method: isotonic_val                # none | isotonic_val
  max_pr_auc_drop: 0.005
operating_point_path: configs/operating_point.yaml
bootstrap:
  n_resamples: 200
evaluation:
  degenerate_eps: 1.0e-9              # score std below this sets degenerate_scores flag
explain:
  shap_background_rows: 1000
  shap_eval_rows: 2000
  n_local_examples: 3
  pdp_top_features: 5
fairness:
  slice_dimensions: [type, amount_band, orig_balance_band, step_band]
  label: "operational error-slice analysis"
compute:
  n_jobs: 4
  omp_num_threads: 4
disclaimer_ref: aml_triage.constants.DISCLAIMER
```

## configs/schema.yaml
```yaml
columns:                              # expected; confirmed by V2
  step: {dtype: int32, nullable: false, min: 1}
  type: {dtype: category, nullable: false}
  amount: {dtype: float32, nullable: false, min: 0, min_is_soft: true}
  nameOrig: {dtype: string, nullable: false, role: identifier}
  oldbalanceOrg: {dtype: float32, nullable: false}
  newbalanceOrig: {dtype: float32, nullable: false, availability: batch_only}
  nameDest: {dtype: string, nullable: false, role: identifier}
  oldbalanceDest: {dtype: float32, nullable: false}
  newbalanceDest: {dtype: float32, nullable: false, availability: batch_only}
  isFraud: {dtype: int8, nullable: false, allowed: [0, 1], role: target}
  isFlaggedFraud: {dtype: int8, nullable: false, allowed: [0, 1], role: rule_comparator}
sensitive_attribute_scan:
  names: [age, gender, sex, ethnicity, race, nationality, income, socioeconomic, region, zip, postcode]
```

## configs/features.yaml — entry shape
```yaml
- name: log_amount
  source_columns: [amount]
  transform: aml_triage.features.transaction.log1p_amount
  rationale: "Amounts are heavy-tailed; log scale stabilizes linear models and trees alike."
  available_at_prediction_time: realtime
  kind: numeric
  sets: [primary, strict_pretx, posttx_ablation]
  dictionary_entry: {type: float, unit: log(currency units), range_or_values: ">= 0", description: "log(1 + amount)"}
```

## configs/models/<id>.yaml — entry shape
```yaml
id: hgb
estimator: sklearn.ensemble.HistGradientBoostingClassifier
params: {class_weight: balanced, random_state: ${seed}, early_stopping: true}
imbalance_strategy: class_weight
feature_set: primary
search_space:
  learning_rate: {loguniform: [0.01, 0.3]}
  max_leaf_nodes: {randint: [15, 127]}
  min_samples_leaf: {randint: [20, 500]}
  l2_regularization: {loguniform: [1e-4, 1.0]}
```

## configs/operating_point.yaml (written by `choose-operating-point`)
```yaml
primary_k: null
threshold: null
threshold_rule: f2_max_on_val
priority_rule: {high: rank_le_k, medium: above_threshold, low: below_threshold}
k_score_cutoff: null            # score of the K-th ranked validation transaction; API uses it in place of rank
calibration: {method: null, decision_log: null}
chosen_on: val
frozen_at: null
```

## configs/vocabulary.yaml
```yaml
prohibited_applied_to_outputs: [fraudulent transaction, launderer, guilty, confirmed fraud, "is fraud", blocked, block transaction, close account, risk rating, SAR, suspicious activity report, regulatory filing]
allowed_phrases: [simulated fraud, isFraud, rule flag, isFlaggedFraud, "fraud label", "no automatic blocking"]
fairness_forbidden_when_unavailable: [demographic fairness result, protected-group fairness, bias audit by protected group]
required_literal: "operational error-slice analysis"
scan_paths: [src, reports, notebooks, README.md, docs]
```
