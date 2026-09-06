"""Request/response models mirroring specs/001-aml-risk-triage/contracts/scoring-api.yaml.

`extra="forbid"` on both models: unknown request fields are rejected (422) and the response can
never carry a decision field such as allow/block/hold/filing (constitution Principle IX).
"""

from __future__ import annotations

from typing import Literal

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
