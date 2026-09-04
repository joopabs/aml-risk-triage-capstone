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
