> Human-authored narrative fragment; `build-report` merges the `## ` sections below into the generated report and this preamble is not merged. Disclaimer: Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.

## Interpretation (task T041, written 2026-09-05 after reviewing the tables and figures above)

Nine components are needed to reach 95% of the variance of the 12 standardised numeric and
aggregate features, and the first two explain only 28.0% and 14.2%. Variance is spread evenly, so
the numeric block is not highly redundant apart from three known pairs: `log_amount`/`amount_bucket`
(both load +0.45 on PC1), the two destination aggregates (PC4), and the two origin aggregates, which
form components PC3 and PC8 on their own. Those origin aggregates are near-constant in raw units;
standardisation inflates them to unit variance, which is why they earn two components while
carrying no information (eda_07). This is a diagnostic confirmation that they belong out of the
model.

In the projection (`pca_02_projection.png`) positives concentrate along a narrow ray with negative
PC1 and PC2 rising to about 30. PC2 loads on `dest_balance_delta` (+0.59), `amount_to_orig_balance_ratio`
(+0.57) and `orig_balance_delta` (+0.36) against `log_oldbalance_org` (−0.34): it is the
"amount moves the whole origin balance to the destination" direction seen in `eda_09`. Normals spread
along positive PC1 (large amounts, funded destinations with prior activity). The classes overlap near
the origin, so two components separate only the extreme positives.

## Do components enter any model?

No. The configured role is diagnostic and visualisation. The primary candidates use raw engineered
features because:

- the artifact ablation (research R-06) needs artifact-driven and behavioural features kept separate,
  and every component mixes both (PC2 blends the balance deltas with the ratio);
- SHAP and PDP explanations on raw features are readable by investigators; explanations on
  components are not;
- tree ensembles gain nothing from an orthogonal rotation of inputs.

A `pca_variant` matrix (9 components plus the type one-hot; fit scope `['train']`) is written so
Milestone 5 can run one documented experiment and report whether the rotation costs or gains
anything. No performance claim is made here.
