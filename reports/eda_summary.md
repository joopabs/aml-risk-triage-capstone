# EDA Summary

## Scope

Figures below use the **training split** (steps 1–408) unless labeled descriptive; class-conditional plots use all training positives plus a seeded sample of negatives. No modeling decision here uses validation or test rows. Observations are written by a human in `reports/eda_narrative.md` after viewing each figure (task T036).

## Training split: rows and positives by type

| type | normal | positive | positive rate |
|---|---|---|---|
| CASH_IN | 1,313,389 | 0 | 0.0000 |
| CASH_OUT | 2,115,988 | 2,304 | 0.0011 |
| DEBIT | 38,489 | 0 | 0.0000 |
| PAYMENT | 2,019,717 | 0 | 0.0000 |
| TRANSFER | 495,245 | 2,285 | 0.0046 |

## Flag features: positive rate by value (training split)

| flag | value | n | positive rate |
|---|---|---|---|
| orig_zero_balance_flag | 0 | 3,990,733 | 0.0011 |
| orig_zero_balance_flag | 1 | 1,996,684 | 0.0000 |
| dest_zero_balance_flag | 0 | 3,452,391 | 0.0005 |
| dest_zero_balance_flag | 1 | 2,535,026 | 0.0012 |
| zero_amount_flag | 0 | 5,987,413 | 0.0008 |
| zero_amount_flag | 1 | 4 | 1.0000 |
| dest_is_merchant | 0 | 3,967,700 | 0.0012 |
| dest_is_merchant | 1 | 2,019,717 | 0.0000 |
| orig_balance_inconsistent_flag | 0 | 1,682,688 | 0.0027 |
| orig_balance_inconsistent_flag | 1 | 4,304,729 | 0.0000 |
| dest_balance_inconsistent_flag | 0 | 1,038,716 | 0.0011 |
| dest_balance_inconsistent_flag | 1 | 4,948,701 | 0.0007 |
| orig_zero_after_flag | 0 | 4,564,614 | 0.0000 |
| orig_zero_after_flag | 1 | 1,422,803 | 0.0032 |

## Class balance by type

![Class balance by type](figures/eda/eda_01_class_by_type.png)

Figure: `eda_01_class_by_type.png`

Observation: Training positives exist only in CASH_OUT (2,304 of 2,118,292 rows, 0.109%) and TRANSFER (2,285 of
497,530, 0.459%). CASH_IN, DEBIT and PAYMENT carry zero positives across 3.37 million rows. Type is
therefore the first-order feature, and TRANSFER has about four times the positive rate of CASH_OUT.
Any model must still score the three positive-free types, which will dominate the low end of the
ranking.

## Amount by class

![Amount by class](figures/eda/eda_02_amount_by_class.png)

Figure: `eda_02_amount_by_class.png`

Observation: Positives sit to the right of normals on log1p(amount): their mode is around 13–14 versus a bimodal
normal distribution peaking near 9.5 and 12.3. Two spikes are artifacts rather than behaviour: a
narrow spike at about 16.1, which is log1p of the 10,000,000 cap seen in the TRANSFER quantiles
(DQ-07), and a small spike at 0 from the zero-amount rows (DQ-03). `log_amount` is informative but
its extreme values are simulator boundaries.

## Amount by type and class

![Amount by type and class](figures/eda/eda_03_amount_by_type_class.png)

Figure: `eda_03_amount_by_type_class.png`

Observation: Within CASH_OUT the positive median amount (about 13 on the log scale) is a full log unit above the
normal median (about 12). Within TRANSFER the medians are similar, near 13, but positives have a wider
interquartile range and their maximum stops at the 16.1 cap while normal TRANSFER amounts reach about
18. Amount separates classes inside CASH_OUT much better than inside TRANSFER.

## Volume and positives over time

![Volume and positives over time](figures/eda/eda_04_volume_positives_over_time.png)

Figure: `eda_04_volume_positives_over_time.png`

Observation: Daily volume runs at roughly 400,000–575,000 transactions on days 1–2 and 6–17 and collapses to
about 1,000–58,000 on days 3–5 and 18–31, a change of nearly three orders of magnitude. Positives per
day stay between 216 and 320 throughout. This confirms DQ-10: simulated fraud is injected at a
near-constant rate independent of volume. The split boundaries (dashed) place validation and test in
the low-volume regime.

## Prevalence by day

![Prevalence by day](figures/eda/eda_05_prevalence_by_day.png)

Figure: `eda_05_prevalence_by_day.png`

Observation: Prevalence on high-volume training days is 0.05%–0.07%. It jumps to about 29% on day 3 and 2.5% on
day 5 (low-volume training days), sits between 0.4% and 2.3% across validation days, and between 0.4%
and 3.3% across test days, with day 31 at 100% because only 272 transactions exist and all are
positive. Validation and test prevalence are more than ten times training prevalence. Probability
calibration fitted on training will be off in validation and test; this is why the operating point
and any calibration are fitted on validation (FR-044, research R-09).

## Correlation heatmap

![Correlation heatmap](figures/eda/eda_06_correlation_heatmap.png)

Figure: `eda_06_correlation_heatmap.png`

Observation: Rank correlations with the label (inflated by the positive-enriched sample, direction only): highest
positive are `orig_zero_after_flag` (0.25), `orig_balance_delta` (0.24), `log_oldbalance_org` (0.16),
`log_amount` (0.15); highest negative are `orig_balance_inconsistent_flag` (−0.23), `dest_is_merchant`
(−0.11), `orig_zero_balance_flag` (−0.10). Origin aggregates correlate with nothing (0.00 everywhere),
confirming DQ-11 that origins do not repeat. Strong collinearity to remember for feature selection:
`amount_bucket`/`log_amount` (0.99), `dest_prior_txn_count`/`dest_prior_amount_sum` (0.98),
`log_oldbalance_dest` with the destination aggregates (0.88–0.91) and with `dest_zero_balance_flag`
(−0.89), `amount_to_orig_balance_ratio` with `log_oldbalance_org` (−0.92), and `dest_is_merchant` with
`dest_zero_balance_flag` (0.81). PDP/ICE for these pairs will need caveats (FR-062).

## Feature distributions by class

![Feature distributions by class](figures/eda/eda_07_feature_distributions.png)

Figure: `eda_07_feature_distributions.png`

Observation: Positives concentrate in the top amount decile (bucket 9) at roughly five times the normal density.
Normals have a large mass at zero origin balance while positives are centred near log 13, so
positives come from funded accounts. `log1p(amount_to_orig_balance_ratio)` for positives spikes at
about 0.69, which is a ratio of 1: the transaction empties the account. Positives are spread almost
uniformly over the 24 hours while normals concentrate in hours 8–20. `orig_balance_delta` for
positives has a long right tail to 10,000,000. `orig_prior_txn_count` and `orig_prior_amount_sum` are
degenerate at zero for both classes and carry no information (candidates to drop in Milestone 4).
Destination aggregates show positives more often going to a destination with no prior activity.

## Flag positive rates

![Flag positive rates](figures/eda/eda_08_flag_positive_rates.png)

Figure: `eda_08_flag_positive_rates.png`

Observation: From the flag table: `zero_amount_flag` = 1 has 4 training rows, all positive (DQ-03 artifact).
`dest_is_merchant` = 1 (2,019,717 rows) has zero positives. `orig_zero_balance_flag` = 1 (1,996,684
rows) has a positive rate of 0.0015%, about 70 times lower than when the balance is non-zero.
`orig_zero_after_flag` = 1 has a rate of 0.32% versus 0.002% when 0, a factor of about 160.
`orig_balance_inconsistent_flag` = 1 (4,304,729 rows) has a rate of 0.0016% versus 0.27% when the
arithmetic is consistent: simulated fraud rows have exact bookkeeping while most normal rows do not.
This is the clearest simulator artifact among the batch-only features and the reason the strict
pre-transaction set is evaluated alongside the primary set (research R-06). `dest_zero_balance_flag`
and `dest_balance_inconsistent_flag` move the rate by less than a factor of three.

## Amount vs origin balance

![Amount vs origin balance](figures/eda/eda_09_amount_vs_origbalance.png)

Figure: `eda_09_amount_vs_origbalance.png`

Observation: Positives lie almost exactly on the diagonal amount = oldbalanceOrg from about log 5 to log 16.1, then
form a horizontal plateau at 16.1 where the 10,000,000 cap binds. Normals form a broad cloud plus a
vertical band at zero balance. The "empty the account" pattern is the dominant visual signature of
simulated fraud and is captured by `amount_to_orig_balance_ratio` and `orig_zero_after_flag`.

## Hour of day

![Hour of day](figures/eda/eda_10_hour_of_day.png)

Figure: `eda_10_hour_of_day.png`

Observation: Hours 0–7 carry very few training rows (tens of thousands or fewer) but positive rates between 1% and
20%; hours 8–19 carry 270,000–620,000 rows each with rates of 0.03%–0.1%; rates rise again after hour
20. Because positives are injected uniformly across the day while normal volume follows a daytime
schedule, `step_hour_of_day` is informative, but the mechanism is the simulator's clock rather than
behaviour, and this must be said in the report.

## Destination prior count

![Destination prior count](figures/eda/eda_11_dest_prior_count.png)

Figure: `eda_11_dest_prior_count.png`

Observation: Positives more often target a destination with zero prior transactions (density about 5.4 versus 3.7
for normals) and are under-represented at higher prior counts. The destination aggregates carry
modest signal in the expected direction; the origin aggregates do not (see eda_07) and are flagged
for removal in feature selection (validation task V10).


---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
