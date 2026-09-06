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


class ServiceError(RuntimeError):
    pass


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
        self._explainer = None

    # ---- feature assembly ---------------------------------------------------------------------
    def _raw_frame(self, req: dict[str, Any]) -> pd.DataFrame:
        if self.known_types and req["type"] not in self.known_types:
            raise UnknownTypeError(f"type must be one of {self.known_types}")
        return pd.DataFrame(
            {
                "step": [int(req["step"])],
                "type": pd.Categorical([req["type"]], categories=self.known_types or [req["type"]]),
                "amount": [float(req["amount"])],
                "nameOrig": [PLACEHOLDER_CUSTOMER],
                "oldbalanceOrg": [float(req["oldbalanceOrg"])],
                "newbalanceOrig": [float(req["newbalanceOrig"])],
                "nameDest": [
                    PLACEHOLDER_MERCHANT if req.get("dest_is_merchant") else PLACEHOLDER_CUSTOMER
                ],
                "oldbalanceDest": [float(req["oldbalanceDest"])],
                "newbalanceDest": [float(req["newbalanceDest"])],
                "row_index": [0],
            }
        )

    def features(self, req: dict[str, Any]) -> pd.DataFrame:
        raw = self._raw_frame(req)
        parts = [raw[["type", "amount"]], compute_stateless(raw, self.defs)]
        if self.aggregate_names:
            parts.append(
                pd.DataFrame(
                    {
                        n: [
                            float(req.get(n, 0)) if "sum" in n else int(req.get(n, 0))
                            for _ in range(1)
                        ]
                        for n in self.aggregate_names
                    }
                )
            )
        engineered = pd.concat(parts, axis=1)
        X = self.feature_pipeline.transform(engineered)
        X = X[self.feature_list] if list(X.columns) != self.feature_list else X
        return X

    # ---- scoring -----------------------------------------------------------------------------
    def priority(self, raw_score: float) -> str:
        if raw_score >= float(self.op["k_score_cutoff"]):
            return "high"
        if raw_score >= float(self.op["threshold"]):
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

    def score(self, req: dict[str, Any]) -> dict[str, Any]:
        X = self.features(req)
        raw = float(self.estimator.predict_proba(X)[:, 1][0])
        display = (
            float(self.calibrator.predict(np.array([raw]))[0])
            if self.calibrator is not None
            else raw
        )
        return {
            "risk_score": float(min(1.0, max(0.0, display))),
            "review_priority": self.priority(raw),
            "model_version": self.version,
            "top_contributing_features": self.explain(X),
        }
