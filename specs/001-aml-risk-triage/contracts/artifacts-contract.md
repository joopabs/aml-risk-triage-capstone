# Artifacts Contract

Physical formats for entities in [data-model.md](../data-model.md). All JSON is UTF-8, keys in
snake_case, timestamps ISO-8601 UTC. Every Markdown artifact ends with the disclaimer footer.

## data/processed/split_manifest.json
```json
{
  "strategy": "temporal",
  "train_end_step": null, "val_end_step": null,
  "rows": {"train": 0, "val": 0, "test": 0},
  "positives": {"train": 0, "val": 0, "test": 0},
  "step_ranges": {"train": [0, 0], "val": [0, 0], "test": [0, 0]},
  "review_period_steps": null,
  "excluded_rows": {},
  "config_hash": "sha256:…",
  "fallback_reason": null,
  "created_at": "…", "frozen_at": null
}
```
(Values are filled by `split`; nulls above are placeholders, not defaults.)

## data/processed/test_access.json
```json
{"config_hash": "sha256:…", "state": "frozen", "frozen_at": "…",
 "first_evaluated_at": null, "reevaluations": []}
```

## models/runs/<candidate>/<split>_metrics.json and models/<version>/metrics.json
```json
{
  "candidate_id": "hgb", "split": "val", "feature_set": "primary",
  "model_version": "…", "config_hash": "sha256:…", "timestamp": "…",
  "k_grid": [],
  "metrics": {
    "prevalence": 0.0, "pr_auc": 0.0, "roc_auc": 0.0,
    "precision": 0.0, "recall": 0.0, "f1": 0.0, "fpr": 0.0,
    "brier": 0.0, "ece": 0.0, "accuracy": 0.0,
    "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
    "recall_at_k": {"<K>": {"mean_over_periods": 0.0, "pooled": 0.0}},
    "precision_at_k": {"<K>": {"mean_over_periods": 0.0, "pooled": 0.0}}
  },
  "per_period": [{"period_index": 0, "step_range": [0, 0], "n_rows": 0, "n_positives": 0,
                  "k_effective": 0, "hits": 0, "recall_at_k": null, "precision_at_k": 0.0}],
  "bootstrap_ci": {"pr_auc": [0.0, 0.0], "recall_at_k": [0.0, 0.0], "n_resamples": 0} ,
  "disclaimer": "…"
}
```
Zeros are schema placeholders; real values are `[MEASURED]` at evaluation.

## models/<version>/
- `pipeline.joblib` — fitted pipeline; `pipeline.sha256` committed alongside.
- `config_snapshot.yaml` — effective merged config.
- `feature_list.json` — `["feature_name", …]` in input order.
- `model_card.md` — sections: Model Details, Intended Use, Non-Use, Data (provenance, synthetic
  notice, license), Metrics (val/test tables with CIs), Operating Point, Explainability Summary,
  Limitations, Fairness Statement (availability result), Version and Checksums, Disclaimer.
- `models/LATEST` — single line: version id.

## reports/fairness_availability.json
```json
{"attributes_checked": ["age","gender","ethnicity","nationality","socioeconomic_status"],
 "proxy_scan_columns": [], "per_attribute": {"age": {"present": false, "evidence": "…"}},
 "any_valid_label": false, "decided_on": "YYYY-MM-DD"}
```

## reports/bias_fairness_analysis.md — required headings (in order)
1. Sensitive-Attribute Availability Record
2. Demographic Fairness (metrics table, or the sentence "Demographic fairness metrics cannot be
   computed on this dataset because no valid sensitive-group labels exist.")
3. Operational Error-Slice Analysis (heading text is literal; FR-073)
4. Limitations
5. Mitigations
6. Governance-Controlled Fairness Audit Plan

## reports/review_queue_period_<i>.md
Table columns: rank, row_index, step, type, risk_score, review_priority, model_version.
Footer: disclaimer. No other columns permitted.

## configs/data_source.yaml
```yaml
name: PaySim - Synthetic Financial Datasets for Fraud Detection
url: https://www.kaggle.com/datasets/ealaxi/paysim1
filename: null            # set at first download
sha256: null              # set at first download
downloaded_on: null
license_text_verbatim: null   # copied from the Kaggle page (V1)
license_verified_on: null
synthetic_notice: "PaySim is synthetic mobile-money transaction data. It is not real SME, corporate, or Philippine banking data."
```
