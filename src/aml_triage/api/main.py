"""FastAPI app for the optional local scoring demo (specs/001-aml-risk-triage/contracts/scoring-api.yaml)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from aml_triage.api.schemas import HealthResponse, ScoreResponse, TransactionRequest
from aml_triage.api.service import ScoringService, UnknownTypeError
from aml_triage.constants import DISCLAIMER

DESCRIPTION = (
    "Educational decision-support prototype trained on synthetic PaySim data. Returns a risk score "
    "and review-priority recommendation for human investigator triage. It does not block transactions, "
    "close accounts, rate customers, file reports, or make AML determinations."
)


def create_app(models_dir: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = ScoringService(models_dir)
        yield

    app = FastAPI(
        title="AML Transaction-Risk Triage Demo API (OPTIONAL Step 8)",
        version="0.1.0",
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

    return app


app = create_app()
