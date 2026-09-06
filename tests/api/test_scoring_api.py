from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from aml_triage.api.main import create_app
from aml_triage.constants import DISCLAIMER, PROHIBITED_OUTPUT_FIELDS

CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "001-aml-risk-triage"
    / "contracts"
    / "scoring-api.yaml"
)
EXAMPLE = json.loads((CONTRACT.parent / "examples" / "score_request.json").read_text())


@pytest.fixture(scope="module")
def client(api_bundle):
    with TestClient(create_app(api_bundle)) as c:
        yield c


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert (
        set(body) == {"status", "model_version", "disclaimer"}
        and body["status"] == "ok"
        and body["disclaimer"] == DISCLAIMER
    )


def test_score_matches_contract(client) -> None:
    r = client.post("/score", json=EXAMPLE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "risk_score",
        "review_priority",
        "model_version",
        "top_contributing_features",
        "disclaimer",
    }
    assert 0.0 <= body["risk_score"] <= 1.0 and body["review_priority"] in {"high", "medium", "low"}
    assert body["disclaimer"] == DISCLAIMER
    assert not (set(body) & set(PROHIBITED_OUTPUT_FIELDS))
    for c in body["top_contributing_features"]:
        assert (
            set(c) == {"feature", "contribution", "plain_language"}
            and "the risk score" in c["plain_language"]
        )


def test_missing_field_is_422(client) -> None:
    bad = {k: v for k, v in EXAMPLE.items() if k != "amount"}
    assert client.post("/score", json=bad).status_code == 422


def test_unknown_field_is_422(client) -> None:
    assert client.post("/score", json={**EXAMPLE, "block": True}).status_code == 422


def test_unknown_type_is_422(client) -> None:
    assert client.post("/score", json={**EXAMPLE, "type": "WIRE"}).status_code == 422


def test_account_emptied_ranks_high(client) -> None:
    drained = {
        **EXAMPLE,
        "type": "TRANSFER",
        "amount": 250000.0,
        "oldbalanceOrg": 250000.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 250000.0,
    }
    normal = {
        **EXAMPLE,
        "type": "PAYMENT",
        "amount": 50.0,
        "oldbalanceOrg": 5000.0,
        "newbalanceOrig": 4950.0,
        "dest_is_merchant": True,
    }
    assert (
        client.post("/score", json=drained).json()["risk_score"]
        > client.post("/score", json=normal).json()["risk_score"]
    )


def test_openapi_matches_contract_fields(client) -> None:
    spec = yaml.safe_load(CONTRACT.read_text())
    generated = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("TransactionRequest", "ScoreResponse"):
        assert set(spec["components"]["schemas"][name]["properties"]) == set(
            generated[name]["properties"]
        ), name
        assert generated[name].get("additionalProperties") is False
