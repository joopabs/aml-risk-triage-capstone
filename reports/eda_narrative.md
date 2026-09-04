# EDA observations (task T036, written 2026-09-05 after viewing each figure)

Each block below is merged into `reports/eda_summary.md` under the matching figure. Numbers are
read from the figures and the two tables in that report (training split unless stated).

### eda_01_class_by_type.png
Training positives exist only in CASH_OUT (2,304 of 2,118,292 rows, 0.109%) and TRANSFER (2,285 of
497,530, 0.459%). CASH_IN, DEBIT and PAYMENT carry zero positives across 3.37 million rows. Type is
therefore the first-order feature, and TRANSFER has about four times the positive rate of CASH_OUT.
Any model must still score the three positive-free types, which will dominate the low end of the
ranking.

### eda_02_amount_by_class.png
Positives sit to the right of normals on log1p(amount): their mode is around 13–14 versus a bimodal
normal distribution peaking near 9.5 and 12.3. Two spikes are artifacts rather than behaviour: a
narrow spike at about 16.1, which is log1p of the 10,000,000 cap seen in the TRANSFER quantiles
(DQ-07), and a small spike at 0 from the zero-amount rows (DQ-03). `log_amount` is informative but
its extreme values are simulator boundaries.

### eda_03_amount_by_type_class.png
Within CASH_OUT the positive median amount (about 13 on the log scale) is a full log unit above the
normal median (about 12). Within TRANSFER the medians are similar, near 13, but positives have a wider
interquartile range and their maximum stops at the 16.1 cap while normal TRANSFER amounts reach about
18. Amount separates classes inside CASH_OUT much better than inside TRANSFER.

### eda_04_volume_positives_over_time.png
Daily volume runs at roughly 400,000–575,000 transactions on days 1–2 and 6–17 and collapses to
about 1,000–58,000 on days 3–5 and 18–31, a change of nearly three orders of magnitude. Positives per
day stay between 216 and 320 throughout. This confirms DQ-10: simulated fraud is injected at a
near-constant rate independent of volume. The split boundaries (dashed) place validation and test in
the low-volume regime.

### eda_05_prevalence_by_day.png
Prevalence on high-volume training days is 0.05%–0.07%. It jumps to about 29% on day 3 and 2.5% on
day 5 (low-volume training days), sits between 0.4% and 2.3% across validation days, and between 0.4%
and 3.3% across test days, with day 31 at 100% because only 272 transactions exist and all are
positive. Validation and test prevalence are more than ten times training prevalence. Probability
calibration fitted on training will be off in validation and test; this is why the operating point
and any calibration are fitted on validation (FR-044, research R-09).

### eda_06_correlation_heatmap.png
Rank correlations with the label (inflated by the positive-enriched sample, direction only): highest
positive are `orig_zero_after_flag` (0.25), `orig_balance_delta` (0.24), `log_oldbalance_org` (0.16),
`log_amount` (0.15); highest negative are `orig_balance_inconsistent_flag` (−0.23), `dest_is_merchant`
(−0.11), `orig_zero_balance_flag` (−0.10). Origin aggregates correlate with nothing (0.00 everywhere),
confirming DQ-11 that origins do not repeat. Strong collinearity to remember for feature selection:
`amount_bucket`/`log_amount` (0.99), `dest_prior_txn_count`/`dest_prior_amount_sum` (0.98),
`log_oldbalance_dest` with the destination aggregates (0.88–0.91) and with `dest_zero_balance_flag`
(−0.89), `amount_to_orig_balance_ratio` with `log_oldbalance_org` (−0.92), and `dest_is_merchant` with
`dest_zero_balance_flag` (0.81). PDP/ICE for these pairs will need caveats (FR-062).

### eda_07_feature_distributions.png
Positives concentrate in the top amount decile (bucket 9) at roughly five times the normal density.
Normals have a large mass at zero origin balance while positives are centred near log 13, so
positives come from funded accounts. `log1p(amount_to_orig_balance_ratio)` for positives spikes at
about 0.69, which is a ratio of 1: the transaction empties the account. Positives are spread almost
uniformly over the 24 hours while normals concentrate in hours 8–20. `orig_balance_delta` for
positives has a long right tail to 10,000,000. `orig_prior_txn_count` and `orig_prior_amount_sum` are
degenerate at zero for both classes and carry no information (candidates to drop in Milestone 4).
Destination aggregates show positives more often going to a destination with no prior activity.

### eda_08_flag_positive_rates.png
From the flag table: `zero_amount_flag` = 1 has 4 training rows, all positive (DQ-03 artifact).
`dest_is_merchant` = 1 (2,019,717 rows) has zero positives. `orig_zero_balance_flag` = 1 (1,996,684
rows) has a positive rate of 0.0015%, about 70 times lower than when the balance is non-zero.
`orig_zero_after_flag` = 1 has a rate of 0.32% versus 0.002% when 0, a factor of about 160.
`orig_balance_inconsistent_flag` = 1 (4,304,729 rows) has a rate of 0.0016% versus 0.27% when the
arithmetic is consistent: simulated fraud rows have exact bookkeeping while most normal rows do not.
This is the clearest simulator artifact among the batch-only features and the reason the strict
pre-transaction set is evaluated alongside the primary set (research R-06). `dest_zero_balance_flag`
and `dest_balance_inconsistent_flag` move the rate by less than a factor of three.

### eda_09_amount_vs_origbalance.png
Positives lie almost exactly on the diagonal amount = oldbalanceOrg from about log 5 to log 16.1, then
form a horizontal plateau at 16.1 where the 10,000,000 cap binds. Normals form a broad cloud plus a
vertical band at zero balance. The "empty the account" pattern is the dominant visual signature of
simulated fraud and is captured by `amount_to_orig_balance_ratio` and `orig_zero_after_flag`.

### eda_10_hour_of_day.png
Hours 0–7 carry very few training rows (tens of thousands or fewer) but positive rates between 1% and
20%; hours 8–19 carry 270,000–620,000 rows each with rates of 0.03%–0.1%; rates rise again after hour
20. Because positives are injected uniformly across the day while normal volume follows a daytime
schedule, `step_hour_of_day` is informative, but the mechanism is the simulator's clock rather than
behaviour, and this must be said in the report.

### eda_11_dest_prior_count.png
Positives more often target a destination with zero prior transactions (density about 5.4 versus 3.7
for normals) and are under-represented at higher prior counts. The destination aggregates carry
modest signal in the expected direction; the origin aggregates do not (see eda_07) and are flagged
for removal in feature selection (validation task V10).

### V10 summary for Milestone 4
Informative: type one-hot, log_amount, amount_bucket, log_oldbalance_org, amount_to_orig_balance_ratio,
orig_zero_balance_flag, orig_zero_after_flag, orig_balance_delta, orig_balance_inconsistent_flag,
dest_is_merchant, step_hour_of_day, dest_prior_txn_count, dest_prior_amount_sum. Weak: dest_zero_balance_flag,
dest_balance_inconsistent_flag, dest_balance_delta, log_oldbalance_dest. Uninformative: orig_prior_txn_count,
orig_prior_amount_sum. Artifact-driven (keep, report as such): zero_amount_flag, orig_balance_inconsistent_flag,
the 10,000,000 amount cap, and hour-of-day.
