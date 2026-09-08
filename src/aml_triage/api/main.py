"""FastAPI app for the optional local scoring demo (specs/001-aml-risk-triage/contracts/scoring-api.yaml)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from aml_triage.api.batch import score_batch
from aml_triage.api.schemas import (
    BatchRequest,
    BatchResponse,
    HealthResponse,
    ScoreResponse,
    TransactionRequest,
    TriageConfig,
)
from aml_triage.api.service import ScoringService, UnknownTypeError
from aml_triage.constants import DISCLAIMER

DESCRIPTION = (
    "Educational decision-support prototype trained on synthetic PaySim data. Returns a risk score "
    "and review-priority recommendation for human investigator triage (one transaction via /score, "
    "a ranked batch via /score-batch). It does not block transactions, close accounts, rate "
    "customers, file reports, or make AML determinations. Request bodies are processed in memory "
    "and never logged or stored."
)


def create_app(models_dir: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = ScoringService(models_dir)
        yield

    app = FastAPI(
        title="AML Transaction-Risk Triage Demo API (OPTIONAL Step 8)",
        version="0.2.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok", model_version=app.state.service.version, disclaimer=DISCLAIMER
        )

    @app.post(
        "/score",
        response_model=ScoreResponse,
        responses={
            422: {"description": "Validation error (missing or invalid field); no score produced"}
        },
    )
    def score(req: TransactionRequest) -> ScoreResponse:
        try:
            out = app.state.service.score(req.model_dump())
        except UnknownTypeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ScoreResponse(**out, disclaimer=DISCLAIMER)

    # ---- feature 002: batch scoring for the optional UI ---------------------------------------
    @app.get("/triage-config", response_model=TriageConfig)
    def triage_config() -> TriageConfig:
        """Frozen operating point values, batch limit, and model version in use. """ + DESCRIPTION
        svc = app.state.service
        return TriageConfig(
            model_version=svc.version,
            batch_limit=svc.batch_limit,
            primary_k=int(svc.op["primary_k"]),
            threshold=float(svc.op["threshold"]),
            disclaimer=DISCLAIMER,
        )

    @app.post(
        "/score-batch",
        response_model=BatchResponse,
        responses={
            413: {"description": "More transactions than the batch limit; nothing scored"},
            422: {
                "description": "Structural error (empty list, malformed body, unknown top-level field); "
                "row-level problems are reported in `skipped`, never as 422"
            },
        },
    )
    def score_batch_endpoint(req: BatchRequest) -> BatchResponse:
        """Score and rank a batch of transactions for review prioritization. """ + DESCRIPTION
        svc = app.state.service
        if len(req.transactions) > svc.batch_limit:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"batch of {len(req.transactions)} transactions exceeds the batch limit of "
                    f"{svc.batch_limit}; nothing scored"
                ),
            )
        return score_batch(svc, req)

    return app


app = create_app()
