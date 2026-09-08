"""Time the batch endpoint and the UI render at the batch limit on synthetic rows (spec SC-006, V1).

Builds N synthetic request rows with the project's generator, scores them in-process through the
FastAPI app (no sockets) with explain=high, then renders the Streamlit app headlessly via AppTest
on the same batch. Prints seconds; nothing is written. Uses the released bundle in models/LATEST
(pass --models-dir for another bundle).

Usage: python scripts/time_batch.py [--rows 5000] [--models-dir models]
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

import pandas as pd


def synthetic_rows(n: int) -> list[dict]:
    from aml_triage.utils.synthetic import make_synthetic_frame

    df = make_synthetic_frame(
        seed=21, n_rows=n, n_steps=200, n_positives=max(1, n // 100), plant_defects=False
    )
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
                "dest_is_merchant": str(r.nameDest).startswith("M"),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--models-dir", default="models")
    a = ap.parse_args()
    os.environ["AML_BATCH_LIMIT"] = str(max(a.rows, 5000))

    from fastapi.testclient import TestClient

    from aml_triage.api.main import create_app

    rows = synthetic_rows(a.rows)
    with TestClient(create_app(a.models_dir)) as c:
        t0 = time.perf_counter()
        r = c.post("/score-batch", json={"transactions": rows, "explain": "high"})
        t_batch = time.perf_counter() - t0
        r.raise_for_status()
        body = r.json()
        print(
            f"POST /score-batch: {a.rows:,} rows in {t_batch:.2f} s (high={body['counts']['high']}, medium={body['counts']['medium']}, low={body['counts']['low']}; model {body['model_version']})"
        )

        # UI render on the same batch, headless, with the in-process client
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            print("streamlit not installed; UI render timing skipped")
            return 0
        sys.path.insert(0, str(Path("tests").resolve()))
        from ui.conftest import InProcessTriageClient  # type: ignore[import-not-found]

        csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode()
        at = AppTest.from_file("src/aml_triage/ui/app.py", default_timeout=600)
        at.session_state["client"] = InProcessTriageClient(c)
        at.run()
        t0 = time.perf_counter()
        at.file_uploader(key="uploader").set_value(("timing.csv", csv_bytes, "text/csv")).run()
        t_parse = time.perf_counter() - t0
        t0 = time.perf_counter()
        at.button(key="score").click().run()
        t_render = time.perf_counter() - t0
        n_table = len(at.dataframe[0].value) if at.dataframe else 0
        print(
            f"UI: parse+load {t_parse:.2f} s; score+render {t_render:.2f} s (table rows={n_table})"
        )
    _ = io  # keep import for potential buffer use
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
