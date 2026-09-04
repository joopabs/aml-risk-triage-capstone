"""File I/O helpers and artifact versioning."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

MODEL_VERSION_PATTERN = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{7}-\w+$")


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    df.to_parquet(p, index=False)
    return p


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(obj: Any, path: str | Path) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")
    return p


def save_joblib(obj: Any, path: str | Path) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    joblib.dump(obj, p)
    return p


def load_joblib(path: str | Path) -> Any:
    return joblib.load(path)


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_short_sha(default: str = "0000000") -> str:
    """Return the 7-character git sha of HEAD, or ``default`` outside a repository."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return default
    sha = out.stdout.strip()
    return sha if re.fullmatch(r"[0-9a-f]{7}", sha) else default


def model_version(
    candidate_id: str, now: datetime | None = None, git_sha: str | None = None
) -> str:
    """Build ``<UTC yyyymmddTHHMMSS>-<git short sha>-<candidate_id>``."""
    if not re.fullmatch(r"\w+", candidate_id):
        raise ValueError("candidate_id must be alphanumeric/underscore")
    ts = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S")
    sha = git_sha or git_short_sha()
    version = f"{ts}-{sha}-{candidate_id}"
    if not MODEL_VERSION_PATTERN.match(version):
        raise ValueError(f"generated model version is malformed: {version}")
    return version
