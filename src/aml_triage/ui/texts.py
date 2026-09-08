"""Every fixed, user-visible string of the batch-triage UI (contracts/ui-contract.md).

Kept in one module so the vocabulary test scans it and so no screen retypes the disclaimer.
Placeholders in braces are filled with ``str.format``.
"""

from __future__ import annotations

from aml_triage.constants import DISCLAIMER

TITLE = "Batch Transaction-Risk Triage (educational prototype, synthetic data)"
PURPOSE = (
    "Orders a batch of synthetic PaySim-style transactions for human review using the released "
    "model and its frozen operating point. It returns a risk score and a review priority per row; "
    "a human investigator reviews, decides, and can override."
)
PRIVACY_NOTE = (
    "Uploaded and typed data is processed in memory and is not stored, logged, or sent anywhere "
    "except the local scoring service."
)
SYNTHETIC_NOTE = "PaySim is synthetic mobile-money data. It is not real SME, corporate, or Philippine banking data."
RULE_TEXT = (
    "Rows are ranked by model score within this batch. `high` means within review capacity "
    "K = {k} and at or above the validation-chosen threshold; `medium` means above the threshold "
    "but outside capacity; `low` otherwise. This is a review order, not a determination."
)
BELOW_CAPACITY = "This batch has fewer rows than the review capacity K = {k}."
SINGLE_ROW = "A single row is not ranked; its priority uses the score bands of the single-transaction service."
SERVICE_DOWN = "The scoring service is not reachable at {url}. Start it with `make api` and reload."
UNKNOWN_COLUMNS = "Unknown columns: {cols}. Only the schema columns are accepted."
EMPTY_FILE = "Nothing to score: the file has no data rows."
OVER_LIMIT = "This file has {n} rows; the batch limit is {limit} rows."
UNREADABLE = "Could not read the file as UTF-8 CSV."
BATCH_TOO_LARGE = "The service refused the batch: {detail}"
BAD_REQUEST = "The service rejected the request: {detail}"

TAB_UPLOAD = "Upload CSV"
TAB_MANUAL = "Enter rows"
BTN_SCORE = "Score batch"
BTN_CLEAR = "Clear batch"
BTN_EXAMPLE = "Load synthetic example"
BTN_DOWNLOAD_QUEUE = "Download ranked queue (CSV)"
BTN_DOWNLOAD_SKIPPED = "Download skipped rows (CSV)"

SIDEBAR_STATUS = "Scoring service"
SIDEBAR_REACHABLE = "reachable at {url}"
SIDEBAR_MODEL = "Model version: `{version}`"
SIDEBAR_OP = "Frozen operating point: K = {k}, threshold = {threshold}"
SIDEBAR_LIMIT = "Batch limit: {limit} rows"
EXPECTED_COLUMNS = (
    "Expected columns (required): step, type, amount, oldbalanceOrg, newbalanceOrig, "
    "oldbalanceDest, newbalanceDest. Optional (default 0 / false): orig_prior_txn_count, "
    "orig_prior_amount_sum, dest_prior_txn_count, dest_prior_amount_sum, dest_is_merchant. "
    "No identifiers are accepted."
)
EXAMPLE_LABEL = "Synthetic example batch ({n} rows) loaded from `{path}`."
LOADED = "{n} rows loaded from {source}. Press **{btn}** to rank them."
SUMMARY = (
    "Received {received} rows: {scored} scored, {skipped} skipped. Review priority: "
    "{high} high, {medium} medium, {low} low. Model `{version}`."
)
VALIDATION_TITLE = "Skipped rows ({n})"
VALIDATION_LINE = "row {input_row}: `{field}` — {reason}"
DUPLICATES = "{n} duplicate rows in the batch (scored and ranked independently)."
EXPLAIN_TITLE = "Why is this row where it is?"
EXPLAIN_SELECT = "Input row"
EXPLAIN_HEADER = (
    "Rank {rank} · priority **{priority}** · risk score {score:.4f} · model `{version}`"
)
EXPLAIN_NONE = "No explanation is available for this row."
NOT_RANKED = "not ranked"
QUEUE_TITLE = "Ranked review queue"

__all__ = [name for name in dir() if name.isupper()] + ["DISCLAIMER"]
