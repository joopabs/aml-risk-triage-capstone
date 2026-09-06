> Human-authored narrative fragment; `build-report` merges the `## ` sections below into the generated report and this preamble is not merged. Disclaimer: Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.

## Verdict reasoning (task T059, written 2026-09-05 after reviewing the matrix above)

**Selected: `hgb [primary]`** (histogram gradient boosting, tuned, on the headline `primary` set). The
verdict was fixed on validation before the test split was unlocked and did not change afterwards.

Reading the matrix column by column:

- **PR-AUC (primary metric).** Three eligible candidates tie or nearly tie on validation:
  `hgb [primary]` 1.0000, `balanced_rf [primary]` 1.0000, `logreg [primary]` 0.9987. The
  deterministic key therefore moves to the next columns for the first two and drops the linear
  model on the primary metric alone. On test the order holds: 1.0000 [1.0000, 1.0000],
  0.9997 [0.9992, 1.0000], 0.9954 [0.9922, 0.9977].
- **Recall@200 and Precision@200.** Identical for every eligible candidate on both splits
  (0.8029 on validation, 0.7568 on test, Precision@200 = 1.0000). Both are ceilings set by K (see
  `capacity_analysis.md`); this column cannot separate the strong candidates.
- **Calibration.** `hgb [primary]` has the lowest validation Brier and ECE (both rounding to 0.0000)
  versus 0.0004 / 0.0046 for `balanced_rf [primary]` and 0.0003 / 0.0065 for `logreg [primary]`.
  This is the column that decides between the two tied tree models.
- **Explainability.** The matrix ranks logistic regression higher (exact linear coefficients).
  Gradient boosting is rated medium: SHAP TreeExplainer is exact and PDP/ICE are valid on raw
  features, so investigator-facing explanations remain feasible (Milestone 7). Explainability was
  not reached by the key because calibration already separated the tied models; had it been reached
  it would have favoured the linear model over the forest.
- **Inference and maintenance cost.** Full-train fit time 20.9 s for `hgb`, 18.6 s for `logreg`,
  135.7 s for `balanced_rf` (506 tuned trees). The forest is the most expensive to retrain and to
  explain locally.
- **Investigator workload.** At the 0.5 threshold on validation `hgb [primary]` produces 0 false
  positives; the forest and the linear model produce 5 each. All three fill the top 200 with positives.

**Why not the strict pre-transaction set.** `hgb [strict_pretx]` (comparison only) equals the selected
model on validation (PR-AUC 1.0000, Brier 0.0000) and is within noise on test (0.9995
[0.9986, 1.0000]). It is prediction-time safe, which `primary` is not. The headline set is `primary`
by project decision (batch triage framing, research R-06); the report presents the strict run beside
the selected one, and a real-time deployment would be better served by it.

**Feature-set honesty.** `hgb [posttx_ablation]`, built only from type plus the five post-transaction
fields, also reaches 1.0000 on both splits. Together with `strict_pretx` at 0.9995 this shows that
both the artifact features and the behavioural features are individually sufficient to reproduce
PaySim's label; the selected model's performance is not evidence of transferable AML skill.

**Process notes.** The operating point was frozen twice before any test access: the first freeze
used a threshold of 1.0 produced by isotonic calibration collapsing validation scores to 0/1; the
rule was corrected to threshold and rank on raw scores and the split was re-frozen (recorded under
`refreezes` in `data/processed/test_access.json`). Two evaluation attempts were killed by the
operating system for memory before any run finished the protocol; the state never reached
`evaluated` until the successful single run, and no test result was seen before the operating point
was final.
