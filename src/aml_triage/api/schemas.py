"""Request/response models mirroring specs/001-aml-risk-triage/contracts/scoring-api.yaml.

`extra="forbid"` on both models: unknown request fields are rejected (422) and the response can
never carry a decision field such as allow/block/hold/filing (constitution Principle IX).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, description="Simulation time step (hour index)")
    type: str = Field(description="Transaction type; must be one of the types seen in training")
    amount: float = Field(ge=0)
    oldbalanceOrg: float
    newbalanceOrig: float = Field(description="Batch-only field; available in end-of-period triage")
    oldbalanceDest: float
    newbalanceDest: float = Field(description="Batch-only field")
    orig_prior_txn_count: int = Field(
        default=0, ge=0, description="Caller-supplied causal aggregate; identifiers are not sent"
    )
    orig_prior_amount_sum: float = Field(default=0.0, ge=0)
    dest_prior_txn_count: int = Field(default=0, ge=0)
    dest_prior_amount_sum: float = Field(default=0.0, ge=0)
    dest_is_merchant: bool = Field(
        default=False,
        description="Destination is a merchant account; from account type, never an identifier",
    )


class Contribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str
    contribution: float
    plain_language: str


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_score: float = Field(ge=0.0, le=1.0)
    review_priority: Literal["high", "medium", "low"] = Field(
        description="Derived from the frozen operating point; a recommendation for human review order only"
    )
    model_version: str
    top_contributing_features: list[Contribution] = Field(default_factory=list, max_length=5)
    disclaimer: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    model_version: str
    disclaimer: str


# ---- feature 002: batch scoring (specs/002-batch-triage-ui/contracts/batch-scoring-api.yaml) ----
ExplainMode = Literal["high", "none", "all"]
ReviewPriority = Literal["high", "medium", "low"]


class BatchRequest(BaseModel):
    """Rows are typed loosely on purpose: each is validated individually as a TransactionRequest so one
    invalid row is reported in `skipped` instead of failing the whole batch (spec FR-012)."""

    model_config = ConfigDict(extra="forbid")

    transactions: list[Any] = Field(
        min_length=1,
        description="Position in the array + 1 is the row's input_row; length must not exceed the batch limit",
    )
    explain: ExplainMode = Field(
        default="high",
        description="Which rows receive top_contributing_features: the high band (default), none, or all",
    )


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_row: int = Field(ge=1)
    field: str = Field(description="Field name, or `_row` for a row-level problem")
    reason: str


class ScoredRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_row: int = Field(ge=1)
    rank: int | None = Field(
        default=None,
        ge=1,
        description="1..n over valid rows; null when the batch has a single valid row (not ranked)",
    )
    risk_score: float = Field(
        ge=0.0, le=1.0, description="Same quantity as POST /score for this row"
    )
    review_priority: ReviewPriority = Field(
        description=(
            "Batch rule: high if rank <= primary_k AND score >= threshold (frozen operating point, "
            "score compared at 6 decimals); medium if score >= threshold; low otherwise. "
            "A recommendation for human review order only."
        )
    )
    top_contributing_features: list[Contribution] = Field(default_factory=list, max_length=5)


class OperatingPointOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_k: int = Field(ge=1)
    threshold: float = Field(ge=0.0, le=1.0)


class Counts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received: int
    scored: int
    skipped: int
    high: int
    medium: int
    low: int


class BatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str
    operating_point: OperatingPointOut
    batch_limit: int
    ranked: bool = Field(description="true when two or more rows were valid")
    counts: Counts
    rows: list[ScoredRow] = Field(description="In rank order; the single row when not ranked")
    skipped: list[ValidationIssue]
    disclaimer: str


class TriageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str
    batch_limit: int = Field(description="Env AML_BATCH_LIMIT, default 5000")
    primary_k: int
    threshold: float
    disclaimer: str
