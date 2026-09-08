# Export Format: ranked queue and skipped rows

**Date**: 2026-09-08 | **Plan**: [../plan.md](../plan.md)

Both exports are UTF-8 CSV with a byte-order mark, comma separated, `\n` line endings, built in
memory by `src/aml_triage/ui/export.py` and offered through the browser download only.

## Line 1 (both files)

`# ` followed by the disclaimer verbatim (`aml_triage.constants.DISCLAIMER`), as a single line.
Readers that honour comment lines (`pandas.read_csv(..., comment="#")`) skip it; spreadsheet
applications show it in cell A1 above the header.

## Ranked queue — `triage_queue_<model_version>.csv`

Header (line 2), then one row per scored transaction in rank order:

| Column | Source |
|---|---|
| rank | ScoredRow.rank (empty when the batch was not ranked) |
| review_priority | ScoredRow.review_priority |
| risk_score | ScoredRow.risk_score, 6 decimals |
| input_row | ScoredRow.input_row |
| step, type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest, orig_prior_txn_count, orig_prior_amount_sum, dest_prior_txn_count, dest_prior_amount_sum, dest_is_merchant | the input values as received (schema order; defaults filled where the input omitted an optional column) |
| model_version | BatchResponse.model_version |

No other columns. In particular no raw score, no label, and no field from the prohibited list.

## Skipped rows — `triage_skipped_<model_version>.csv`

Header (line 2), then one line per validation issue (a row with two failing fields appears twice):

| Column | Source |
|---|---|
| input_row | ValidationIssue.input_row |
| field | ValidationIssue.field |
| reason | ValidationIssue.reason |
| step, type, amount, … (schema order) | the raw input values as received, unmodified strings; missing values empty |

## Tests (tests/ui/test_export.py)

- First line starts with `# ` and equals the disclaimer.
- Queue header equals the column list above; rows are in ascending rank; row count equals
  `counts.scored`.
- Skipped file row count equals `len(skipped)`; input values are echoed unmodified.
- Neither file contains any prohibited field name or vocabulary term.
