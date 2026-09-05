"""Write a seeded synthetic sample CSV for the CI smoke pipeline (no PaySim data involved).

Usage: make_sample.py --config configs/smoke.yaml [--rows 30000] [--positives 300]
The output path is the config's paths.raw_csv. Sized so every split keeps >= min_positives and
each review period holds more positives than the smoke K, mirroring the real capacity regime.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from aml_triage.config import load
from aml_triage.utils.synthetic import make_synthetic_frame


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/smoke.yaml")
    ap.add_argument("--rows", type=int, default=30_000)
    ap.add_argument("--positives", type=int, default=300)
    ap.add_argument("--steps", type=int, default=72)
    a = ap.parse_args()
    cfg = load(a.config)
    cfg.require(["paths.raw_csv"])
    out = Path(cfg.paths.raw_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = make_synthetic_frame(
        seed=cfg.seed, n_rows=a.rows, n_steps=a.steps, n_positives=a.positives, plant_defects=False
    )
    df.to_csv(out, index=False)
    print(f"wrote {out}: {len(df):,} rows, {int(df['isFraud'].sum())} positives, steps 1-{a.steps}")


if __name__ == "__main__":
    main()
