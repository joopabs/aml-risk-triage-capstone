"""API test fixtures. The shared synthetic `api_bundle` fixture lives in tests/conftest.py (feature 002
moved it there so tests/ui can use it); this file holds the batch-scoring fixtures only."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from aml_triage.utils.synthetic import make_synthetic_frame  # noqa: E402

# ---- feature 002: batch scoring fixtures -------------------------------------------------------
REQUEST_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "orig_prior_txn_count",
    "orig_prior_amount_sum",
    "dest_prior_txn_count",
    "dest_prior_amount_sum",
    "dest_is_merchant",
]


def frame_to_rows(df) -> list[dict]:
    """Map synthetic raw rows to request bodies (aggregates 0; merchant flag from the destination prefix)."""
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            {
                "step": int(r.step),
                "type": str(r.type),
                "amount": round(float(r.amount), 2),
                "oldbalanceOrg": round(float(r.oldbalanceOrg), 2),
                "newbalanceOrig": round(float(r.newbalanceOrig), 2),
                "oldbalanceDest": round(float(r.oldbalanceDest), 2),
                "newbalanceDest": round(float(r.newbalanceDest), 2),
                "orig_prior_txn_count": 0,
                "orig_prior_amount_sum": 0.0,
                "dest_prior_txn_count": 0,
                "dest_prior_amount_sum": 0.0,
                "dest_is_merchant": str(r.nameDest).startswith("M"),
            }
        )
    return rows


@pytest.fixture(scope="session")
def batch_rows() -> list[dict]:
    """≥ 30 valid rows incl. the drained-account pattern the fixture model learned."""
    df = make_synthetic_frame(seed=11, n_rows=600, n_steps=72, n_positives=12, plant_defects=False)
    return frame_to_rows(df.head(40))


@pytest.fixture(scope="session")
def drained_rows() -> list[dict]:
    """15 rows that empty the origin account (the positive pattern) with distinct amounts."""
    rows = []
    for i in range(15):
        amt = 50_000.0 + 1_000.0 * i
        rows.append(
            {
                "step": 60 + (i % 5),
                "type": "TRANSFER" if i % 2 else "CASH_OUT",
                "amount": amt,
                "oldbalanceOrg": amt,
                "newbalanceOrig": 0.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": amt,
                "dest_is_merchant": False,
            }
        )
    return rows


@pytest.fixture(scope="session")
def routine_rows() -> list[dict]:
    """12 small merchant payments that leave the origin account funded."""
    return [
        {
            "step": 30 + i,
            "type": "PAYMENT",
            "amount": 20.0 + i,
            "oldbalanceOrg": 5_000.0,
            "newbalanceOrig": 4_980.0 - i,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
            "dest_is_merchant": True,
        }
        for i in range(12)
    ]


@pytest.fixture(scope="session")
def invalid_rows(batch_rows) -> dict[str, dict]:
    """One row per validation failure type, keyed by the field expected in `skipped`."""
    base = dict(batch_rows[0])
    return {
        "amount_missing": {k: v for k, v in base.items() if k != "amount"},
        "amount_non_numeric": {**base, "amount": "lots"},
        "amount_negative": {**base, "amount": -5.0},
        "type_unknown": {**base, "type": "WIRE"},
        "extra_field": {**base, "block": True},
        "step_zero": {**base, "step": 0},
    }


@pytest.fixture(scope="session")
def tie_rows() -> list[dict]:
    """Identical transactions (identical scores) at different steps/positions to exercise the tie-break."""
    row = {
        "type": "CASH_OUT",
        "amount": 7_500.0,
        "oldbalanceOrg": 7_500.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 100.0,
        "newbalanceDest": 7_600.0,
        "dest_is_merchant": False,
    }
    return [{**row, "step": s} for s in (5, 3, 5, 1, 3)]


@pytest.fixture
def post_batch():
    def _post(client, rows, explain: str = "high", expect: int = 200):
        r = client.post("/score-batch", json={"transactions": rows, "explain": explain})
        assert r.status_code == expect, r.text
        return r.json()

    return _post
