"""Fixtures for the optional batch-triage UI tests (specs/002-batch-triage-ui, research R-08).

The UI is driven headlessly with ``streamlit.testing.v1.AppTest``; its HTTP client is replaced by an
in-process client over the real FastAPI app built from the shared synthetic ``api_bundle`` fixture,
so every UI test exercises the actual scoring path without sockets. Skipped when the optional
extras are not installed.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from aml_triage.api.main import create_app  # noqa: E402
from aml_triage.ui.client import BadRequest, BatchTooLarge, ServiceUnavailable  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "src" / "aml_triage" / "ui" / "app.py"
EXAMPLE_CSV = (
    REPO_ROOT / "specs" / "002-batch-triage-ui" / "contracts" / "examples" / "example_batch.csv"
)


class InProcessTriageClient:
    """Same protocol as aml_triage.ui.client.HttpTriageClient, over a FastAPI TestClient."""

    base_url = "in-process"

    def __init__(self, test_client: TestClient, fail: bool = False):
        self._c = test_client
        self._fail = fail

    @staticmethod
    def _strip(row: dict) -> dict:
        return {k: v for k, v in row.items() if k != "input_row"}

    def config(self) -> dict:
        if self._fail:
            raise ServiceUnavailable(self.base_url)
        return self._c.get("/triage-config").json()

    def score_batch(self, rows: list[dict], explain: str = "high") -> dict:
        if self._fail:
            raise ServiceUnavailable(self.base_url)
        r = self._c.post(
            "/score-batch",
            json={"transactions": [self._strip(x) for x in rows], "explain": explain},
        )
        if r.status_code == 413:
            raise BatchTooLarge(r.json().get("detail", ""))
        if r.status_code >= 400:
            raise BadRequest(str(r.json().get("detail", r.text)))
        return r.json()

    def score_one(self, row: dict) -> dict:
        if self._fail:
            raise ServiceUnavailable(self.base_url)
        r = self._c.post("/score", json=self._strip(row))
        if r.status_code >= 400:
            raise BadRequest(str(r.json().get("detail", r.text)))
        return r.json()


@pytest.fixture(scope="session")
def api_client(api_bundle):
    with TestClient(create_app(api_bundle)) as c:
        yield c


@pytest.fixture
def ui_client(api_client) -> InProcessTriageClient:
    return InProcessTriageClient(api_client)


@pytest.fixture
def down_client(api_client) -> InProcessTriageClient:
    return InProcessTriageClient(api_client, fail=True)


@pytest.fixture
def app(ui_client) -> Callable[..., AppTest]:
    """Run the app once with the in-process client injected; extra kwargs seed session state."""

    def _run(client=None, **state) -> AppTest:
        at = AppTest.from_file(str(APP_PATH), default_timeout=120)
        at.session_state["client"] = client or ui_client
        for k, v in state.items():
            at.session_state[k] = v
        return at.run()

    return _run


# ---- CSV builders -------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def example_csv() -> bytes:
    return EXAMPLE_CSV.read_bytes()


def csv_lines(data: bytes) -> list[str]:
    return data.decode("utf-8").splitlines()


@pytest.fixture(scope="session")
def csv_unknown_column(example_csv) -> bytes:
    lines = csv_lines(example_csv)
    lines[0] = lines[0].replace("amount", "nameOrig_amount")
    return ("\n".join(lines) + "\n").encode()


@pytest.fixture(scope="session")
def csv_header_only(example_csv) -> bytes:
    return (csv_lines(example_csv)[0] + "\n").encode()


@pytest.fixture(scope="session")
def csv_with_invalid_rows(example_csv) -> bytes:
    lines = csv_lines(example_csv)
    header = lines[0].split(",")
    row = lines[1].split(",")
    bad_amount = list(row)
    bad_amount[header.index("amount")] = "-5"
    bad_type = list(row)
    bad_type[header.index("type")] = "WIRE"
    lines += [",".join(bad_amount), ",".join(bad_type)]
    return ("\n".join(lines) + "\n").encode()


def csv_over_limit(example_csv: bytes, limit: int) -> bytes:
    lines = csv_lines(example_csv)
    body = lines[1:]
    while len(body) <= limit:
        body += lines[1:]
    return ("\n".join([lines[0], *body]) + "\n").encode()


# ---- filesystem snapshot (SC-007) --------------------------------------------------------------
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}


@pytest.fixture
def fs_snapshot():
    return _fs_snapshot


def _fs_snapshot(*roots: Path) -> str:
    h = hashlib.sha256()
    for root in roots:
        if not root.exists():
            h.update(f"missing:{root}".encode())
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_PARTS)
            for f in sorted(filenames):
                p = Path(dirpath) / f
                try:
                    st = p.stat()
                except OSError:
                    continue
                h.update(f"{p}|{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()
