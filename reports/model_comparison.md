# Model Comparison

## Method

Every candidate is trained on the training split of its feature set and scored on the split named in each section; comparators need no training. Review period = 24 steps; primary K = 200; k_grid = [50, 100, 200, 300, 500]. Threshold metrics use 0.5 until the operating point is chosen on validation (Milestone 6). Accuracy appears last, next to the majority-class baseline, and is never a selection criterion (FR-007). PR-AUC is primary; the no-skill PR-AUC equals prevalence.

## Validation: headline metrics

| candidate [feature set] | PR-AUC | ROC-AUC | Recall@200 (mean/period) | Recall@200 (pooled) | Precision@200 (mean/period) | Brier | ECE | degenerate |
|---|---|---|---|---|---|---|---|---|
| balanced_rf [primary] | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0005 | 0.0090 |  |
| hgb [posttx_ablation] | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0005 | 0.0029 |  |
| hgb [primary] | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0000 | 0.0002 |  |
| hgb [strict_pretx] | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0000 | 0.0004 |  |
| hgb [selected] | 1.0000 | 1.0000 | 0.8029 | 0.7979 | 1.0000 | 0.0002 | 0.0018 |  |
| balanced_rf [strict_pretx] | 0.9997 | 1.0000 | 0.8021 | 0.7972 | 0.9992 | 0.0023 | 0.0187 |  |
| logreg [primary] | 0.9987 | 0.9995 | 0.8029 | 0.7979 | 1.0000 | 0.0003 | 0.0057 |  |
| hgb [pca_variant] | 0.8998 | 0.9976 | 0.7373 | 0.7354 | 0.9217 | 0.0140 | 0.0253 |  |
| logreg [strict_pretx] | 0.2599 | 0.9821 | 0.2945 | 0.2972 | 0.3725 | 0.0583 | 0.0874 |  |
| rule comparator (flag, then amount) | 0.1555 | 0.8142 | 0.1965 | 0.1995 | 0.2500 | 0.0077 | 0.0024 |  |
| random ranking | 0.0084 | 0.5050 | 0.0104 | 0.0106 | 0.0133 | 0.3335 | 0.4919 |  |
| dummy (chronological order) [primary] | 0.0083 | 0.5000 | 0.0650 | 0.0665 | 0.0833 | 0.0083 | 0.0075 | yes |
| dummy [strict_pretx] | 0.0083 | 0.5000 | 0.0650 | 0.0665 | 0.0833 | 0.0083 | 0.0075 | yes |

## Validation: Recall@K across the capacity grid (mean over review periods)

| candidate [feature set] | Recall@50 | Recall@100 | Recall@200 | Recall@300 | Recall@500 |
|---|---|---|---|---|---|
| balanced_rf [primary] | 0.2007 | 0.4015 | 0.8029 | 1.0000 | 1.0000 |
| hgb [posttx_ablation] | 0.2007 | 0.4015 | 0.8029 | 1.0000 | 1.0000 |
| hgb [primary] | 0.2007 | 0.4015 | 0.8029 | 1.0000 | 1.0000 |
| hgb [strict_pretx] | 0.2007 | 0.4015 | 0.8029 | 1.0000 | 1.0000 |
| hgb [selected] | 0.2007 | 0.4015 | 0.8029 | 1.0000 | 1.0000 |
| balanced_rf [strict_pretx] | 0.2007 | 0.4015 | 0.8021 | 1.0000 | 1.0000 |
| logreg [primary] | 0.2007 | 0.4015 | 0.8029 | 0.9988 | 0.9988 |
| hgb [pca_variant] | 0.2007 | 0.4007 | 0.7373 | 0.8689 | 0.9276 |
| logreg [strict_pretx] | 0.0642 | 0.1458 | 0.2945 | 0.4072 | 0.5659 |
| rule comparator (flag, then amount) | 0.0927 | 0.1352 | 0.1965 | 0.2351 | 0.3102 |
| random ranking | 0.0013 | 0.0026 | 0.0104 | 0.0130 | 0.0220 |
| dummy (chronological order) [primary] | 0.0457 | 0.0528 | 0.0650 | 0.0925 | 0.1513 |
| dummy [strict_pretx] | 0.0457 | 0.0528 | 0.0650 | 0.0925 | 0.1513 |

## Validation: Precision@K across the capacity grid (mean over review periods)

| candidate [feature set] | Precision@50 | Precision@100 | Precision@200 | Precision@300 | Precision@500 |
|---|---|---|---|---|---|
| balanced_rf [primary] | 1.0000 | 1.0000 | 1.0000 | 0.8356 | 0.5013 |
| hgb [posttx_ablation] | 1.0000 | 1.0000 | 1.0000 | 0.8356 | 0.5013 |
| hgb [primary] | 1.0000 | 1.0000 | 1.0000 | 0.8356 | 0.5013 |
| hgb [strict_pretx] | 1.0000 | 1.0000 | 1.0000 | 0.8356 | 0.5013 |
| hgb [selected] | 1.0000 | 1.0000 | 1.0000 | 0.8356 | 0.5013 |
| balanced_rf [strict_pretx] | 1.0000 | 1.0000 | 0.9992 | 0.8356 | 0.5013 |
| logreg [primary] | 1.0000 | 1.0000 | 1.0000 | 0.8344 | 0.5007 |
| hgb [pca_variant] | 1.0000 | 0.9983 | 0.9217 | 0.7267 | 0.4657 |
| logreg [strict_pretx] | 0.3267 | 0.3700 | 0.3725 | 0.3433 | 0.2860 |
| rule comparator (flag, then amount) | 0.4733 | 0.3433 | 0.2500 | 0.1989 | 0.1567 |
| random ranking | 0.0067 | 0.0067 | 0.0133 | 0.0111 | 0.0113 |
| dummy (chronological order) [primary] | 0.2333 | 0.1350 | 0.0833 | 0.0789 | 0.0770 |
| dummy [strict_pretx] | 0.2333 | 0.1350 | 0.0833 | 0.0789 | 0.0770 |

## Validation: threshold metrics at 0.5

| candidate [feature set] | threshold | precision | recall | F1 | FPR | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|
| balanced_rf [primary] | 0.5000 | 0.9993 | 1.0000 | 0.9997 | 0.0000 | 1,504 | 1 | 0 | 179,563 |
| hgb [posttx_ablation] | 0.5000 | 0.9888 | 1.0000 | 0.9944 | 0.0001 | 1,504 | 17 | 0 | 179,547 |
| hgb [primary] | 0.5000 | 0.9993 | 1.0000 | 0.9997 | 0.0000 | 1,504 | 1 | 0 | 179,563 |
| hgb [strict_pretx] | 0.5000 | 0.9954 | 1.0000 | 0.9977 | 0.0000 | 1,504 | 7 | 0 | 179,557 |
| hgb [selected] | 0.5000 | 0.9823 | 0.9987 | 0.9904 | 0.0002 | 1,502 | 27 | 2 | 179,537 |
| balanced_rf [strict_pretx] | 0.5000 | 0.8909 | 0.9993 | 0.9420 | 0.0010 | 1,503 | 184 | 1 | 179,380 |
| logreg [primary] | 0.5000 | 0.9980 | 0.9987 | 0.9983 | 0.0000 | 1,502 | 3 | 2 | 179,561 |
| hgb [pca_variant] | 0.5000 | 0.2866 | 0.9654 | 0.4420 | 0.0201 | 1,452 | 3,614 | 52 | 175,950 |
| logreg [strict_pretx] | 0.5000 | 0.0925 | 0.9820 | 0.1690 | 0.0807 | 1,477 | 14,499 | 27 | 165,065 |
| rule comparator (flag, then amount) | 0.5000 | 1.0000 | 0.0013 | 0.0027 | 0.0000 | 2 | 0 | 1,502 | 179,564 |
| random ranking | 0.5000 | 0.0084 | 0.5073 | 0.0166 | 0.5006 | 763 | 89,883 | 741 | 89,681 |
| dummy (chronological order) [primary] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1,504 | 179,564 |
| dummy [strict_pretx] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1,504 | 179,564 |

## Validation: accuracy (reported last, with prevalence)

| candidate [feature set] | accuracy | prevalence | majority-class accuracy (1 - prevalence) |
|---|---|---|---|
| balanced_rf [primary] | 1.0000 | 0.0083 | 0.9917 |
| hgb [posttx_ablation] | 0.9999 | 0.0083 | 0.9917 |
| hgb [primary] | 1.0000 | 0.0083 | 0.9917 |
| hgb [strict_pretx] | 1.0000 | 0.0083 | 0.9917 |
| hgb [selected] | 0.9998 | 0.0083 | 0.9917 |
| balanced_rf [strict_pretx] | 0.9990 | 0.0083 | 0.9917 |
| logreg [primary] | 1.0000 | 0.0083 | 0.9917 |
| hgb [pca_variant] | 0.9798 | 0.0083 | 0.9917 |
| logreg [strict_pretx] | 0.9198 | 0.0083 | 0.9917 |
| rule comparator (flag, then amount) | 0.9917 | 0.0083 | 0.9917 |
| random ranking | 0.4995 | 0.0083 | 0.9917 |
| dummy (chronological order) [primary] | 0.9917 | 0.0083 | 0.9917 |
| dummy [strict_pretx] | 0.9917 | 0.0083 | 0.9917 |

## Validation: curves

![pr_curves_val](figures/models/pr_curves_val.png)

![roc_curves_val](figures/models/roc_curves_val.png)

![calibration_curves_val](figures/models/calibration_curves_val.png)

## Validation discussion (task T050, written 2026-09-05 after reviewing the tables and curves above)

All numbers below are validation-split figures (steps 409–552, 181,068 rows, 1,504 positives, six
review periods). No test-split number appears here; the test split stays locked until the operating
point is frozen (Milestone 6).

### 1. The simulator is almost perfectly separable, and that is the main finding

Every tree model on every non-PCA feature set reaches PR-AUC 1.0000 and ROC-AUC 1.0000:
`hgb` on `primary`, `strict_pretx`, `selected` and `posttx_ablation`, and `balanced_rf` on `primary`
(`balanced_rf` on `strict_pretx` is 0.9997). At the default 0.5 threshold, `hgb [primary]` makes one
false positive and zero false negatives across 181,068 validation rows. Logistic regression on the
`primary` set is close behind at 0.9987.

This is not evidence of AML capability. PaySim generates its positives from a small set of agent
rules (an account is drained by TRANSFER and CASH_OUT), so a handful of engineered features
reproduce the generator's own rule almost exactly: `amount_to_orig_balance_ratio` near 1,
`orig_zero_after_flag`, and the balance-arithmetic flags (eda_08, eda_09). Any model that can express
"ratio ≈ 1 and type ∈ {TRANSFER, CASH_OUT}" recovers the label. The comparison therefore says a lot
about the dataset and little about which learner would be best on real transactions.

### 2. The artifact ablation (research R-06) reads differently for trees and for the linear model

- For tree models the expected gap between `primary` and `strict_pretx` does **not** appear: `hgb`
  scores 1.0000 on both. The post-transaction artifact features are sufficient on their own
  (`posttx_ablation`, which contains only type plus the five batch-only features, also reaches
  1.0000) but they are not necessary: the pre-transaction interaction between type and the
  amount-to-balance ratio carries the same information for a non-linear learner.
- For logistic regression the gap is large: 0.9987 on `primary` versus 0.2599 on `strict_pretx`,
  with its `strict_pretx` PR curve peaking near 0.36 precision. A linear model cannot express the
  type-by-ratio interaction additively, so it needs the post-transaction flags to do the work.
- `hgb [pca_variant]` reaches 0.8998: rotating the numeric block into nine components mixes the
  ratio with unrelated variance and costs about 0.10 of PR-AUC and 0.07 of Recall@200. Components
  do not enter any further candidate (see `reports/pca_report.md`).

### 3. Recall@K is bounded by K on validation, not by the models

Validation periods hold between 216 and 272 positives, all above K = 200. The best possible mean
Recall@200 is therefore the mean of 200 / positives over the six periods, which is 0.8029; every
strong model hits exactly that ceiling with Precision@200 = 1.0000, meaning all 200 reviewed
transactions in every period are positives. The per-period recall for `hgb [primary]` ranges from
0.735 (272 positives) to 0.926 (216 positives) purely because of the positive count. At K = 300 and
K = 500 the strong models reach 1.0000 because K exceeds the positives; at K = 50 and K = 100 they
all sit at K / positives (0.2007 and 0.4015). Recall@K cannot separate the strong candidates on this
split; it does show that K = 200 binds, which is the intended operational reading.

### 4. Comparators

The rule comparator (flag, then amount) reaches PR-AUC 0.1555 and Recall@200 of 0.1965: amount
alone puts about one positive in five into the daily top 200, and its threshold row shows only two
flagged rows in the whole validation split (precision 1.0, recall 0.0013). Random ranking gives
PR-AUC 0.0084, equal to prevalence (0.0083), and Recall@200 of 0.0104. The dummy candidate's
constant scores rank as chronological order and give Recall@200 of 0.0650. Every learner except
`logreg [strict_pretx]` beats all three comparators by a wide margin; `logreg [strict_pretx]` still
beats them (0.2945 versus 0.1965 at K = 200).

### 5. Calibration

The reliability curves lie below the diagonal in the middle of the score range for every model:
class weighting inflates mid-range scores, as expected. Because the strong models push almost every
row to a score near 0 or 1, their Brier scores are tiny (`hgb [primary]` 0.0000, `logreg [primary]`
0.0003, `balanced_rf [primary]` 0.0005) and ECE is below 0.01 for all of them. `balanced_rf [primary]`
is the least calibrated of the strong models (ECE 0.0090; its 0.55–0.70 bins show observed rates of
0.66–1.00). Whether isotonic calibration fitted on validation helps is decided in Milestone 6 under
the configured tolerance (research R-09); ranking metrics are unaffected by a monotone map.

### 6. What this means for selection (Milestone 6)

PR-AUC and Recall@K cannot discriminate between `hgb` (any set), `balanced_rf [primary]` and
`logreg [primary]` on validation. The selection matrix must therefore lean on the other columns the
spec requires: calibration quality, explainability, inference and maintenance cost (fit times 31 s,
72 s and 18 s respectively on 5.99 million rows), feature-set honesty (`hgb [strict_pretx]` is
prediction-time safe and equally strong), and behaviour under the validation-to-test regime shift,
which only the single-touch test evaluation can show. The headline feature set remains `primary`
by project decision; the report will show `strict_pretx` beside it.

### 7. Caveats

- Six review periods is a small sample; per-period recall varies with the positive count alone.
- Perfect validation separability is a property of PaySim's generator and will not transfer to real
  banking data. Nothing here establishes real-world detection effectiveness.
- Threshold metrics use 0.5 pending the validation-chosen operating point.


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
