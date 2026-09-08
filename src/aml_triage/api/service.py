"""Scoring service: loads the released bundle once and scores single transactions.

Scoring reuses the bundle's fitted feature pipeline and estimator exactly as trained. Ranking-style
priority uses the frozen operating point's score-only bands (research/data-model §8): high if the
raw score is at or above the K-th validation score cutoff, medium if at or above the threshold,
low otherwise. The displayed probability is the validation-calibrated score when a calibrator
exists. Request bodies are never logged or persisted.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aml_triage.explain.captions import direction_phrase, human_name
from aml_triage.features.base import compute_stateless, features_for_set, load_registry
from aml_triage.utils.io import load_joblib

PLACEHOLDER_CUSTOMER = "C0"  # placeholder identifiers exist only so prefix-based transforms run
PLACEHOLDER_MERCHANT = "M0"
OPERATING_POINT_DECIMALS = (
    6  # precision at which choose-operating-point stores threshold and k_score_cutoff
)


DEFAULT_BATCH_LIMIT = 5000  # rows per POST /score-batch; deployment setting AML_BATCH_LIMIT


class ServiceError(RuntimeError):
    pass


def _batch_limit_from_env() -> int:
    raw = os.environ.get("AML_BATCH_LIMIT", str(DEFAULT_BATCH_LIMIT))
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ServiceError(f"AML_BATCH_LIMIT must be an integer >= 1, got {raw!r}") from exc
    if limit < 1:
        raise ServiceError(f"AML_BATCH_LIMIT must be >= 1, got {limit}")
    return limit


class UnknownTypeError(ValueError):
    pass


class ScoringService:
    def __init__(self, models_dir: str | Path | None = None):
        models_dir = Path(models_dir or os.environ.get("AML_MODELS_DIR", "models"))
        latest = models_dir / "LATEST"
        if not latest.exists():
            raise ServiceError(
                f"{latest} not found; release a bundle with `python -m aml_triage select`"
            )
        self.version = latest.read_text().strip()
        bundle_dir = models_dir / self.version
        self.bundle: dict[str, Any] = load_joblib(bundle_dir / "pipeline.joblib")
        self.estimator = self.bundle["estimator"]
        self.feature_pipeline = self.bundle["feature_pipeline"]
        self.calibrator = self.bundle.get("calibrator")
        self.op = self.bundle["operating_point"]
        self.feature_list: list[str] = self.bundle["feature_list"]
        registry_path = bundle_dir / "features.yaml"
        self.defs = features_for_set(load_registry(registry_path), self.bundle["feature_set"])
        self.aggregate_names = [d.name for d in self.defs if d.is_aggregate]
        onehot = self.feature_pipeline.named_transformers_.get("type_onehot")
        self.known_types: list[str] = (
            [str(c) for c in onehot.categories_[0]] if onehot is not None else []
        )
        self.batch_limit: int = _batch_limit_from_env()
        self._explainer = None

    # ---- feature assembly ---------------------------------------------------------------------
    def _raw_frame(self, reqs: list[dict[str, Any]]) -> pd.DataFrame:
        """Raw-schema frame for one or more validated requests (placeholder identifiers only)."""
        for req in reqs:
            if self.known_types and req["type"] not in self.known_types:
                raise UnknownTypeError(f"type must be one of {self.known_types}")
        return pd.DataFrame(
            {
                "step": [int(r["step"]) for r in reqs],
                "type": pd.Categorical(
                    [r["type"] for r in reqs],
                    categories=self.known_types or sorted({r["type"] for r in reqs}),
                ),
                "amount": [float(r["amount"]) for r in reqs],
                "nameOrig": [PLACEHOLDER_CUSTOMER] * len(reqs),
                "oldbalanceOrg": [float(r["oldbalanceOrg"]) for r in reqs],
                "newbalanceOrig": [float(r["newbalanceOrig"]) for r in reqs],
                "nameDest": [
                    PLACEHOLDER_MERCHANT if r.get("dest_is_merchant") else PLACEHOLDER_CUSTOMER
                    for r in reqs
                ],
                "oldbalanceDest": [float(r["oldbalanceDest"]) for r in reqs],
                "newbalanceDest": [float(r["newbalanceDest"]) for r in reqs],
                "row_index": list(range(len(reqs))),
            }
        )

    def features_many(self, reqs: list[dict[str, Any]]) -> pd.DataFrame:
        """Engineered feature matrix for many requests through the fitted training-time pipeline."""
        raw = self._raw_frame(reqs)
        parts = [raw[["type", "amount"]], compute_stateless(raw, self.defs)]
        if self.aggregate_names:
            parts.append(
                pd.DataFrame(
                    {
                        n: [
                            float(r.get(n, 0) or 0) if "sum" in n else int(r.get(n, 0) or 0)
                            for r in reqs
                        ]
                        for n in self.aggregate_names
                    }
                )
            )
        engineered = pd.concat(parts, axis=1)
        X = self.feature_pipeline.transform(engineered)
        X = X[self.feature_list] if list(X.columns) != self.feature_list else X
        return X

    def features(self, req: dict[str, Any]) -> pd.DataFrame:
        return self.features_many([req])

    # ---- scoring -----------------------------------------------------------------------------
    def priority(self, raw_score: float) -> str:
        # The sealed operating point stores its cutoffs rounded to 6 decimals, so compare at that
        # precision: a raw score of 0.99997689 belongs to the 0.999977 band it was rounded into.
        # Comparing the unrounded score against the rounded cutoff made the high band unreachable.
        score = round(float(raw_score), OPERATING_POINT_DECIMALS)
        if score >= float(self.op["k_score_cutoff"]):
            return "high"
        if score >= float(self.op["threshold"]):
            return "medium"
        return "low"

    def explain(self, X: pd.DataFrame, top: int = 3) -> list[dict[str, Any]]:
        try:
            import shap

            if self._explainer is None:
                self._explainer = shap.TreeExplainer(self.estimator)
            vals = np.asarray(self._explainer.shap_values(X))
            if vals.ndim == 3:
                vals = vals[:, :, -1]
            v = vals[0]
        except Exception:  # model without tree explainer: fall back to no explanation
            return []
        order = np.argsort(-np.abs(v))[:top]
        return [
            {
                "feature": self.feature_list[j],
                "contribution": float(v[j]),
                "plain_language": f"{human_name(self.feature_list[j])} (= {float(X.iloc[0, j]):,.2f}) {direction_phrase(float(v[j]))} the risk score by {abs(float(v[j])):.2f} log-odds",
            }
            for j in order
        ]

    def explain_row(self, X: pd.DataFrame, i: int, top: int = 3) -> list[dict[str, Any]]:
        """Factors for row ``i`` of a feature matrix (same explainer as the single path)."""
        return self.explain(X.iloc[[i]], top=top)

    def score_many(self, reqs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """Raw scores, displayed (calibrated, clipped) scores, and the feature matrix for many rows.

        One feature build and one ``predict_proba`` call; the single-transaction ``score`` is this
        with one row, so batch and single scores are identical by construction.
        """
        X = self.features_many(reqs)
        raw = self.estimator.predict_proba(X)[:, 1].astype(float)
        display = self.calibrator.predict(raw).astype(float) if self.calibrator is not None else raw
        return raw, np.clip(display, 0.0, 1.0), X

    def score(self, req: dict[str, Any]) -> dict[str, Any]:
        raw, display, X = self.score_many([req])
        return {
            "risk_score": float(display[0]),
            "review_priority": self.priority(float(raw[0])),
            "model_version": self.version,
            "top_contributing_features": self.explain(X),
        }
