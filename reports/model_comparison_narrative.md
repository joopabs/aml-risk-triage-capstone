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

## Test discussion (task T059, single-touch evaluation, written 2026-09-05 after the tables above)

The test split (steps 553–743, 194,135 rows, 2,120 positives, prevalence 1.09%) was scored exactly
once after the operating point was frozen; `data/processed/test_access.json` records the state and
would record any re-evaluation with a reason. Every run was refitted on the full training split with
its tuned parameters before scoring.

**Validation-to-test shift.** Prevalence rises from 0.83% to 1.09% and daily volume stays in the
low-volume regime. Rankings are stable: `hgb [primary]` and `hgb [posttx_ablation]` keep PR-AUC
1.0000 (95% CI [1.0000, 1.0000]); `balanced_rf` on both sets holds at 0.9997; `hgb [strict_pretx]`
moves from 1.0000 to 0.9995 [0.9986, 1.0000]; `hgb [selected]` from 0.9990 to 0.9996;
`logreg [primary]` from 0.9987 to 0.9954 [0.9922, 0.9977]. The linear model on the strict set
improves slightly (0.2776 → 0.2908) and the rule comparator improves from 0.1555 to 0.1856, both
because higher prevalence makes precision easier. No candidate degrades materially, so the regime
shift the split was designed to expose does not hurt tree models on this data.

**Recall@200 is again a K ceiling.** All strong models score 0.7568 (mean) / 0.7547 (pooled) with
Precision@200 = 1.0000, because every test period holds 240–280 positives. The dummy (chronological)
comparator rises to 0.2076 and random to 0.1012 only because day 31 contains 272 rows, all positives,
where any order scores 0.735. See `capacity_analysis.md`.

**Calibration on test.** The reliability curves keep the class-weighting signature (observed rate
below the diagonal in the middle bins), but the strong models place nearly all rows at scores near 0
or 1, so Brier stays tiny: `hgb [primary]` 0.0000 (3 × 10⁻⁶), `hgb [strict_pretx]` 0.0000,
`balanced_rf [primary]` 0.0003, `logreg [primary]` 0.0004. The validation-fitted isotonic
calibrator, used only for the displayed probability, gives Brier 2.8 × 10⁻⁶ and ECE 6 × 10⁻⁶ on test.

**Selected model at its operating point.** `hgb [primary]` at the frozen raw-score threshold 0.9719:
2,115 true positives, 5 false negatives, 0 false positives across 192,015 normals (recall 0.9976,
precision 1.0000). At the default 0.5 threshold it makes 0 errors of either kind on 194,135 rows.

**Caveats carried forward.** Eight review periods; one of them (day 31) is a partial day with 272
transactions. Perfect separation is a property of PaySim, not a transferable result. Bootstrap CIs
resample rows and therefore understate uncertainty about future periods.
