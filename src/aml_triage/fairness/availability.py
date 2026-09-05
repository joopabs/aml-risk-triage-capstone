"""Sensitive-attribute availability record (spec FR-070). Derived from the actual raw columns."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aml_triage.config import Config
from aml_triage.data.load import read_header
from aml_triage.data.schema import load_schema
from aml_triage.utils.io import write_json

ATTRIBUTES = ["age", "gender", "ethnicity", "nationality", "socioeconomic_status"]
PROXIES = {
    "age": ["age", "birth", "dob"],
    "gender": ["gender", "sex"],
    "ethnicity": ["ethnicity", "race"],
    "nationality": ["nationality", "country", "citizen"],
    "socioeconomic_status": [
        "income",
        "socioeconomic",
        "wealth",
        "occupation",
        "education",
        "region",
        "zip",
        "postcode",
    ],
}


def availability_record(cfg: Config) -> dict[str, Any]:
    columns = read_header(cfg.paths.raw_csv)
    schema = load_schema()
    scan_names = sorted(
        set(schema.sensitive_attribute_names) | {p for ps in PROXIES.values() for p in ps}
    )
    lower = {c.lower(): c for c in columns}
    per_attr = {}
    for attr in ATTRIBUTES:
        hits = [lower[c] for c in lower if any(p in c for p in PROXIES[attr])]
        per_attr[attr] = {
            "present": bool(hits),
            "evidence": (
                f"columns matching {PROXIES[attr]}: {hits}"
                if hits
                else f"no column among {columns} contains any of {PROXIES[attr]}"
            ),
        }
    proxy_hits = [lower[c] for c in lower if any(n in c for n in scan_names)]
    record = {
        "attributes_checked": ATTRIBUTES,
        "proxy_scan_names": scan_names,
        "proxy_scan_columns": proxy_hits,
        "raw_columns": columns,
        "per_attribute": per_attr,
        "any_valid_label": any(v["present"] for v in per_attr.values()),
        "decided_on": datetime.now(UTC).date().isoformat(),
        "source": str(cfg.paths.raw_csv),
    }
    write_json(record, Path(cfg.paths.reports_dir) / "fairness_availability.json")
    return record
