"""Temporal train/validation/test split (spec FR-040/041, research R-05).

Rows are assigned by ``step``: train <= train_end_step < val <= val_end_step < test. Every row keeps
its original position as ``row_index`` for deterministic tie-breaks and leakage tests. No row is
excluded: the data-quality review (DQ-01..DQ-13) decided keep/flag for every finding.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

from aml_triage.config import Config
from aml_triage.utils.io import ensure_dir, write_parquet

MANIFEST_NAME = "split_manifest.json"
SPLITS = ("train", "val", "test")
ROW_INDEX = "row_index"


class SplitGuardError(RuntimeError):
    """A split guard failed (too few positives, frozen manifest, bad ranges). Exit code 3."""


@dataclass
class SplitManifest:
    strategy: str
    train_end_step: int | None
    val_end_step: int | None
    rows: dict[str, int]
    positives: dict[str, int]
    step_ranges: dict[str, list[int]]
    review_period_steps: int
    excluded_rows: dict[str, int]
    config_hash: str
    fallback_reason: str | None
    created_at: str
    frozen_at: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"

    @classmethod
    def read(cls, path: str | Path) -> SplitManifest:
        with open(path, encoding="utf-8") as fh:
            return cls(**json.load(fh))


def _assign_temporal(df: pd.DataFrame, train_end: int, val_end: int) -> pd.Series:
    step = df["step"]
    return pd.Series(
        pd.cut(step, bins=[-1, train_end, val_end, step.max()], labels=list(SPLITS)).astype(str),
        index=df.index,
    )


def _assign_stratified(df: pd.DataFrame, seed: int, val_frac: float = 0.15, test_frac: float = 0.15) -> pd.Series:
    idx = df.index.to_numpy()
    y = df["isFraud"].to_numpy()
    rest, test = train_test_split(idx, test_size=test_frac, stratify=y, random_state=seed)
    y_rest = df.loc[rest, "isFraud"].to_numpy()
    train, val = train_test_split(rest, test_size=val_frac / (1 - test_frac), stratify=y_rest, random_state=seed)
    out = pd.Series("train", index=df.index)
    out.loc[val] = "val"
    out.loc[test] = "test"
    return out


def make_split(df: pd.DataFrame, cfg: Config) -> tuple[dict[str, pd.DataFrame], SplitManifest]:
    """Assign rows to splits and validate the guards. ``df`` must be the raw frame in file order."""
    cfg.require(["split.min_positives_per_split", "review.review_period_steps"])
    frame = df.copy()
    frame[ROW_INDEX] = frame.index.to_numpy()
    notes: list[str] = []

    if cfg.split.strategy == "temporal":
        cfg.require(["split.train_end_step", "split.val_end_step"])
        assignment = _assign_temporal(frame, cfg.split.train_end_step, cfg.split.val_end_step)
        notes.append("Temporal split by step; all validation rows are later than all training rows and all test rows later than validation.")
    else:
        if not cfg.split.fallback_reason:
            raise SplitGuardError("stratified_fallback requires split.fallback_reason (FR-041)")
        assignment = _assign_stratified(frame, cfg.seed)
        notes.append("Stratified fallback (FR-041): time-derived aggregate features MUST be excluded downstream.")

    parts = {name: frame.loc[assignment == name] for name in SPLITS}
    positives = {name: int(part["isFraud"].sum()) for name, part in parts.items()}
    rows = {name: int(len(part)) for name, part in parts.items()}
    short = {k: v for k, v in positives.items() if v < cfg.split.min_positives_per_split}
    if short:
        raise SplitGuardError(
            f"positives below split.min_positives_per_split={cfg.split.min_positives_per_split}: {short}"
        )
    if any(v == 0 for v in rows.values()):
        raise SplitGuardError(f"empty split: {rows}")

    step_ranges = {name: [int(part["step"].min()), int(part["step"].max())] for name, part in parts.items()}
    if cfg.split.strategy == "temporal":
        if not (step_ranges["train"][1] < step_ranges["val"][0] <= step_ranges["val"][1] < step_ranges["test"][0]):
            raise SplitGuardError(f"step ranges are not monotone: {step_ranges}")

    manifest = SplitManifest(
        strategy=cfg.split.strategy,
        train_end_step=cfg.split.train_end_step,
        val_end_step=cfg.split.val_end_step,
        rows=rows,
        positives=positives,
        step_ranges=step_ranges,
        review_period_steps=cfg.review.review_period_steps,
        excluded_rows={},
        config_hash=cfg.config_hash(),
        fallback_reason=cfg.split.fallback_reason,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        notes=notes,
    )
    return parts, manifest


def write_split(parts: dict[str, pd.DataFrame], manifest: SplitManifest, processed_dir: str | Path) -> Path:
    out = ensure_dir(processed_dir)
    existing = out / MANIFEST_NAME
    if existing.exists():
        prior = SplitManifest.read(existing)
        if prior.frozen_at:
            # The manifest is tracked in git, so a clean clone starts frozen. Regenerating the (gitignored)
            # parquet files is allowed only when the recomputed partition is identical; the frozen manifest
            # itself is left untouched. Any different partition would invalidate the single-touch test
            # evaluation and is refused.
            if partition_fields(prior) != partition_fields(manifest):
                raise SplitGuardError(f"{existing} is frozen; re-splitting would invalidate the single-touch test evaluation")
            for name, part in parts.items():
                write_parquet(part, out / f"{name}.parquet")
            return existing
    for name, part in parts.items():
        write_parquet(part, out / f"{name}.parquet")
    existing.write_text(manifest.to_json(), encoding="utf-8")
    return existing


def partition_fields(manifest: SplitManifest) -> dict[str, Any]:
    """The fields that define the partition (timestamps and the config hash are provenance, not partition)."""
    return {
        "strategy": manifest.strategy,
        "train_end_step": manifest.train_end_step,
        "val_end_step": manifest.val_end_step,
        "rows": manifest.rows,
        "positives": manifest.positives,
        "step_ranges": manifest.step_ranges,
        "review_period_steps": manifest.review_period_steps,
        "excluded_rows": manifest.excluded_rows,
        "fallback_reason": manifest.fallback_reason,
    }


def load_split(processed_dir: str | Path, name: str) -> pd.DataFrame:
    return pd.read_parquet(Path(processed_dir) / f"{name}.parquet")


def summarize(manifest: SplitManifest) -> dict[str, Any]:
    return {k: v for k, v in asdict(manifest).items() if k != "notes"}
