## Consistency Notes (task T071, written 2026-09-05 after reviewing the figures and tables above)

**Agreement with EDA, feature by feature (top five by mean |SHAP|).**

- `orig_balance_inconsistent_flag` (0.446, rank 1). Beeswarm: the flag at 0 (blue) pushes the
  score up, at 1 (red) pulls it down; the PDP falls from about 0.11 to 0 as the flag goes 0 → 1.
  This matches `eda_08`: positives have exact origin bookkeeping (positive rate 0.27% when the
  arithmetic reconciles versus 0.0016% when it does not). It is the simulator artifact DQ-05, and
  the model's single most important input.
- `orig_zero_after_flag` (0.331, rank 2). Value 1 raises the score; some ICE lines go from 0 to 1.
  Matches `eda_08` (positive rate 0.32% versus 0.002%) and the diagonal in `eda_09`.
- `orig_balance_delta` (0.198, rank 3). Large posted changes raise the score (local example 1:
  a delta of 1,688,761 contributes +4.25 log-odds). Consistent with `eda_07`, where positives carry a
  long right tail. Its PDP is flat because the effect only appears jointly with the two flags above;
  the ICE spread shows that interaction.
- `amount_to_orig_balance_ratio` (0.197, rank 4). Ratios near 1 raise the score (all three local
  examples sit at exactly 1.00). Matches `eda_07` and `eda_09` (the "empty the account" diagonal).
  The PDP grid is dominated by extreme ratios from near-zero balances and shows nothing in the
  informative region near 1; this is a limitation of the grid, not evidence of no effect.
- `type_CASH_OUT` (0.180, rank 5). Consistent with `eda_01`: positives exist only in CASH_OUT and
  TRANSFER.

**Surprises, not omitted.**

- `dest_is_merchant`, `zero_amount_flag`, `type_DEBIT` and both origin aggregates have mean |SHAP|
  of 0.000. For `dest_is_merchant` this is redundancy with `type_PAYMENT`, not irrelevance. For
  `zero_amount_flag` it is scarcity: 4 training rows.
- Permutation importance shows the model depends on exactly two features. Permuting
  `orig_balance_inconsistent_flag` drops PR-AUC by 0.52 and `orig_zero_after_flag` by 0.48; every
  other feature permutes to a drop of 0.008 or less because the remaining signal is recoverable
  from correlated columns. The released model is, in effect, the rule "origin bookkeeping reconciles
  and the origin account was emptied".
- Three of the top four features are post-transaction (batch-only) fields. This is the artifact
  dominance anticipated in research R-06. The `strict_pretx` run reached the same PR-AUC without
  them, so the behavioural signal exists, but the released model prefers the bookkeeping shortcut.

**The five test positives below the operating-point threshold.** Three are zero-amount CASH_OUT rows
with zero balances (raw scores 0.80–0.92); two are TRANSFERs whose posted origin balance did not
change (10,399,045 → 10,399,045 and 5,674,548 → 5,674,548; scores 0.52 and 0.97). All five are
generator edge cases rather than behavioural misses, and all five still rank above every normal
transaction in their period.

## Plain-language summary for a business audience

The model ranks a transaction near the top when the sending account is emptied by the transaction
and the posted balances reconcile exactly, especially for transfers and cash-outs of large amounts
relative to the balance. On this synthetic data that pattern identifies almost every simulated
positive. A real bank's data would not hand the model such a clean bookkeeping signature, so the
explanation method transfers; the specific features that dominate here do not. Investigators see, for
each queued transaction, the three factors that moved its score most and can override the ranking.
