"""Guards that keep isolated configurations (smoke/CI, tests) from writing tracked project files.

The real run writes a few governed files that live in git: the sealed operating point, the feature
registry's ``selected`` markers, and the README tolerance line. An isolated configuration redirects
``paths.*`` to scratch directories; if it keeps a default path for one of those files it silently
overwrites the real, reviewed content (this happened during the T065 clean-clone check). These helpers
make such a write an explicit error (exit code 2 via ``ValueError``).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aml_triage.config import Config

DEFAULT_PROCESSED_DIR = "data/processed"
REPO_ROOT = Path(__file__).resolve().parents[2]


def is_isolated(cfg: Config) -> bool:
    """True when the configuration writes its derived state somewhere other than the real run."""
    return cfg.paths.processed_dir != DEFAULT_PROCESSED_DIR


def guard_tracked_write(cfg: Config, path: str | Path, tracked_default: str, what: str) -> None:
    """Refuse to write ``path`` when it is the repository's tracked ``tracked_default`` and ``cfg`` is isolated."""
    if not is_isolated(cfg):
        return
    if Path(path).resolve() == (REPO_ROOT / tracked_default).resolve():
        raise ValueError(
            f"{what}: {path} is the tracked project file but paths.processed_dir is {cfg.paths.processed_dir!r}; "
            f"isolated configurations must point this path under their own models_dir "
            f"(e.g. {Path(cfg.paths.models_dir) / Path(tracked_default).name}) so the reviewed file is never overwritten"
        )
