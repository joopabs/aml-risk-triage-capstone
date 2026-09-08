"""Client for the local scoring service (specs/002-batch-triage-ui/contracts/batch-scoring-api.yaml).

The UI never loads the model: every score comes from the FastAPI service (the Step 8 deployment of
record) over the loopback interface, so there is exactly one scoring path (spec FR-021). Request
bodies are never logged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import yaml

UI_CONFIG_PATH = Path("configs/ui.yaml")
DEFAULTS: dict[str, Any] = {
    "api_url": "http://127.0.0.1:8000",
    "request_timeout_seconds": 60,
    "explain_default": "high",
    "example_batch": "deployment/ui/example_batch.csv",
}


class TriageClientError(RuntimeError):
    """Base class for client-side failures shown to the user."""


class ServiceUnavailable(TriageClientError):
    def __init__(self, url: str):
        super().__init__(f"scoring service not reachable at {url}")
        self.url = url


class BatchTooLarge(TriageClientError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequest(TriageClientError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class TriageClient(Protocol):
    base_url: str

    def config(self) -> dict[str, Any]: ...

    def score_batch(self, rows: list[dict[str, Any]], explain: str = "high") -> dict[str, Any]: ...

    def score_one(self, row: dict[str, Any]) -> dict[str, Any]: ...


def strip_input_row(row: dict[str, Any]) -> dict[str, Any]:
    """The service identifies rows by position; ``input_row`` is UI bookkeeping only."""
    return {k: v for k, v in row.items() if k != "input_row"}


def load_ui_config(path: str | Path = UI_CONFIG_PATH) -> dict[str, Any]:
    p = Path(path)
    cfg = dict(DEFAULTS)
    if p.exists():
        cfg.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return cfg


class HttpTriageClient:
    """requests-based client; raises typed errors the UI turns into fixed messages."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    @classmethod
    def from_config(cls, path: str | Path = UI_CONFIG_PATH) -> HttpTriageClient:
        cfg = load_ui_config(path)
        return cls(cfg["api_url"], cfg["request_timeout_seconds"])

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        import requests

        try:
            r = requests.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise ServiceUnavailable(self.base_url) from exc
        if r.status_code == 413:
            raise BatchTooLarge(_detail(r))
        if r.status_code >= 400:
            raise BadRequest(_detail(r))
        return r.json()

    def config(self) -> dict[str, Any]:
        return self._request("GET", "/triage-config")

    def score_batch(self, rows: list[dict[str, Any]], explain: str = "high") -> dict[str, Any]:
        payload = {"transactions": [strip_input_row(r) for r in rows], "explain": explain}
        return self._request("POST", "/score-batch", json=payload)

    def score_one(self, row: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/score", json=strip_input_row(row))


def _detail(response: Any) -> str:
    try:
        body = response.json()
    except ValueError:
        return str(response.text)[:500]
    return str(body.get("detail", body))[:500] if isinstance(body, dict) else str(body)[:500]
