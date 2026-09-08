"""Contract tests for the batch extension (specs/002-batch-triage-ui/contracts/batch-scoring-api.yaml).

Every test runs against the synthetic fixture bundle; no real data is read.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from aml_triage.api.main import create_app
from aml_triage.constants import DISCLAIMER, PROHIBITED_OUTPUT_FIELDS

CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "002-batch-triage-ui"
    / "contracts"
    / "batch-scoring-api.yaml"
)
SCHEMAS = yaml.safe_load(CONTRACT.read_text())["components"]["schemas"]
EXAMPLE = json.loads((CONTRACT.parent / "examples" / "batch_request.json").read_text())


@pytest.fixture(scope="module")
def client(api_bundle):
    with TestClient(create_app(api_bundle)) as c:
        yield c


def _keys(schema_name: str) -> set[str]:
    return set(SCHEMAS[schema_name]["properties"])


def _all_keys(obj, acc: set[str]) -> set[str]:
    if isinstance(obj, dict):
        acc.update(obj)
        for v in obj.values():
            _all_keys(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _all_keys(v, acc)
    return acc


# ---- (a) /triage-config ------------------------------------------------------------------------
def test_triage_config_matches_bundle(client) -> None:
    r = client.get("/triage-config")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == _keys("TriageConfig")
    svc = client.app.state.service
    assert body["model_version"] == svc.version
    assert body["primary_k"] == int(svc.op["primary_k"])
    assert body["threshold"] == pytest.approx(float(svc.op["threshold"]))
    assert body["batch_limit"] == svc.batch_limit == 5000
    assert body["disclaimer"] == DISCLAIMER


# ---- (b) response shape ------------------------------------------------------------------------
def test_batch_response_matches_contract(client, post_batch) -> None:
    body = post_batch(client, EXAMPLE["transactions"], EXAMPLE["explain"])
    assert set(body) == _keys("BatchResponse")
    assert set(body["operating_point"]) == _keys("OperatingPoint")
    assert set(body["counts"]) == _keys("Counts")
    for row in body["rows"]:
        assert set(row) == _keys("ScoredRow")
        for c in row["top_contributing_features"]:
            assert set(c) == _keys("Contribution")
    for issue in body["skipped"]:
        assert set(issue) == _keys("ValidationIssue")
    assert body["disclaimer"] == DISCLAIMER
    # the example: 3 valid rows scored, the WIRE row skipped on `type`
    assert body["counts"] == {
        "received": 4,
        "scored": 3,
        "skipped": 1,
        "high": body["counts"]["high"],
        "medium": body["counts"]["medium"],
        "low": body["counts"]["low"],
    }
    assert body["skipped"][0]["input_row"] == 4 and body["skipped"][0]["field"] == "type"
    assert [r["rank"] for r in body["rows"]] == [1, 2, 3]
    assert body["rows"][0]["input_row"] == 1  # the emptied-account TRANSFER ranks first


def test_unknown_top_level_field_is_422(client) -> None:
    r = client.post("/score-batch", json={"transactions": EXAMPLE["transactions"], "decision": "x"})
    assert r.status_code == 422


def test_empty_batch_is_422(client) -> None:
    assert client.post("/score-batch", json={"transactions": []}).status_code == 422


# ---- (c) per-row validation: skip and report ---------------------------------------------------
def test_invalid_rows_are_skipped_and_reported(
    client, post_batch, batch_rows, invalid_rows
) -> None:
    rows = batch_rows[:5] + list(invalid_rows.values())
    body = post_batch(client, rows)
    assert body["counts"]["received"] == len(rows)
    assert body["counts"]["scored"] == 5
    assert body["counts"]["skipped"] == len(invalid_rows)
    by_row = {i["input_row"]: i for i in body["skipped"]}
    expected_fields = {
        6: "amount",  # missing
        7: "amount",  # non-numeric
        8: "amount",  # negative
        9: "type",  # unknown type
        10: "block",  # extra field
        11: "step",  # step 0
    }
    for input_row, field in expected_fields.items():
        assert input_row in by_row, f"row {input_row} not reported"
        assert by_row[input_row]["field"] == field
        assert by_row[input_row]["reason"]
    scored_rows = {r["input_row"] for r in body["rows"]}
    assert scored_rows == {1, 2, 3, 4, 5}


# ---- (d) ranking parity with the pipeline ------------------------------------------------------
def test_rank_batch_matches_pipeline_ranking() -> None:
    from aml_triage.api.batch import rank_batch
    from aml_triage.evaluation.capacity import rank_within_periods

    rng = np.random.default_rng(0)
    n = 200
    scores = np.round(rng.random(n), 2)  # many exact ties
    steps = rng.integers(1, 50, size=n)
    input_rows = np.arange(1, n + 1)
    ranks = rank_batch(scores, steps, input_rows)

    df = pd.DataFrame({"row_index": input_rows, "step": steps, "isFraud": 0, "score": scores})
    ref = (
        rank_within_periods(df, review_period_steps=10**6)
        .sort_values("row_index")["rank"]
        .to_numpy()
    )
    assert np.array_equal(ranks, ref)


def test_tie_break_is_deterministic(client, post_batch, tie_rows) -> None:
    a = post_batch(client, tie_rows)
    b = post_batch(client, tie_rows)
    order_a = [r["input_row"] for r in a["rows"]]
    assert order_a == [r["input_row"] for r in b["rows"]]
    # identical scores: earlier step first, then earlier position
    scores = {r["input_row"]: r["risk_score"] for r in a["rows"]}
    assert len(set(scores.values())) == 1
    assert order_a == [4, 2, 5, 1, 3]


# ---- (e) priority rule -------------------------------------------------------------------------
def test_assign_batch_priority_rule() -> None:
    from aml_triage.api.batch import assign_batch_priority

    k, thr = 10, 0.971931
    assert assign_batch_priority(1, 0.99, k, thr) == "high"
    assert assign_batch_priority(10, 0.9719305, k, thr) == "high"  # rounds to the threshold
    assert assign_batch_priority(11, 0.99, k, thr) == "medium"  # outside capacity
    assert assign_batch_priority(1, 0.5, k, thr) == "low"  # in capacity but below threshold
    assert assign_batch_priority(50, 0.5, k, thr) == "low"


def test_more_than_k_positives_yield_exactly_k_high(client, post_batch, drained_rows) -> None:
    body = post_batch(client, drained_rows)
    k = body["operating_point"]["primary_k"]
    assert len(drained_rows) > k
    assert body["ranked"] is True
    # every drained row scores far above the threshold on the fixture model
    assert body["counts"]["high"] == k
    assert body["counts"]["medium"] == len(drained_rows) - k
    assert [r["rank"] for r in body["rows"]] == list(range(1, len(drained_rows) + 1))
    assert all(r["review_priority"] == "high" for r in body["rows"][:k])


def test_routine_batch_has_no_high_rows(client, post_batch, routine_rows) -> None:
    body = post_batch(client, routine_rows)
    assert body["counts"]["high"] == 0
    assert body["counts"]["scored"] == len(routine_rows)


def test_batch_smaller_than_k(client, post_batch, drained_rows) -> None:
    body = post_batch(client, drained_rows[:3])
    assert body["ranked"] is True and body["counts"]["scored"] == 3
    assert body["counts"]["high"] <= 3 and [r["rank"] for r in body["rows"]] == [1, 2, 3]


def test_single_row_is_not_ranked_and_matches_single_score(
    client, post_batch, drained_rows
) -> None:
    row = drained_rows[0]
    body = post_batch(client, [row])
    single = client.post("/score", json=row).json()
    assert body["ranked"] is False
    assert body["rows"][0]["rank"] is None
    assert body["rows"][0]["review_priority"] == single["review_priority"]
    assert body["rows"][0]["risk_score"] == single["risk_score"]


# ---- (f) score equality with the single-transaction path ---------------------------------------
def test_batch_scores_equal_single_scores(client, post_batch, batch_rows, drained_rows) -> None:
    rows = batch_rows[:20] + drained_rows[:5]
    body = post_batch(client, rows, explain="all")
    by_row = {r["input_row"]: r for r in body["rows"]}
    for i, row in enumerate(rows, start=1):
        single = client.post("/score", json=row).json()
        assert by_row[i]["risk_score"] == single["risk_score"], f"row {i}"
        assert by_row[i]["top_contributing_features"] == single["top_contributing_features"], (
            f"row {i}"
        )


def test_explain_option_controls_factors(client, post_batch, drained_rows, routine_rows) -> None:
    rows = drained_rows[:2] + routine_rows[:2]
    none = post_batch(client, rows, explain="none")
    assert all(r["top_contributing_features"] == [] for r in none["rows"])
    high = post_batch(client, rows, explain="high")
    for r in high["rows"]:
        has = bool(r["top_contributing_features"])
        assert has == (r["review_priority"] == "high")
    every = post_batch(client, rows, explain="all")
    assert all(r["top_contributing_features"] for r in every["rows"])


# ---- (g) structural limits ---------------------------------------------------------------------
def test_batch_limit_is_enforced_and_configurable(api_bundle, monkeypatch, drained_rows) -> None:
    monkeypatch.setenv("AML_BATCH_LIMIT", "3")
    with TestClient(create_app(api_bundle)) as c:
        assert c.get("/triage-config").json()["batch_limit"] == 3
        r = c.post("/score-batch", json={"transactions": drained_rows[:4]})
        assert r.status_code == 413
        assert "3" in r.json()["detail"]
        assert c.post("/score-batch", json={"transactions": drained_rows[:3]}).status_code == 200


# ---- (h) no decision fields anywhere -----------------------------------------------------------
def test_no_prohibited_fields_in_batch_responses(client, post_batch, drained_rows) -> None:
    body = post_batch(client, drained_rows[:4], explain="all")
    keys = _all_keys(body, set())
    assert not (keys & set(PROHIBITED_OUTPUT_FIELDS))
    keys = _all_keys(client.get("/triage-config").json(), set())
    assert not (keys & set(PROHIBITED_OUTPUT_FIELDS))


# ---- (i) no dataset access during scoring ------------------------------------------------------
def test_batch_scoring_reads_no_files(client, post_batch, batch_rows, monkeypatch) -> None:
    def _forbidden(*args, **kwargs):  # pragma: no cover - only hit on regression
        raise AssertionError("batch scoring must not read data files")

    monkeypatch.setattr(pd, "read_parquet", _forbidden)
    monkeypatch.setattr(pd, "read_csv", _forbidden)
    body = post_batch(client, batch_rows[:10], explain="all")
    assert body["counts"]["scored"] == 10
