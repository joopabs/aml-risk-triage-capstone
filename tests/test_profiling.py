from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aml_triage.cli import main
from aml_triage.constants import DISCLAIMER, EXIT_OK, EXIT_VALIDATION
from aml_triage.data.dictionary import DictionaryError, build_dictionary
from aml_triage.data.profiling import profile_frame, run_profile
from aml_triage.data.schema import load_schema


@pytest.fixture(scope="module")
def schema():
    return load_schema()


def test_profile_detects_planted_defects(fixture_frame, schema) -> None:
    prof = profile_frame(fixture_frame, schema)
    assert prof["n_rows"] == len(fixture_frame)
    assert prof["duplicates"]["exact_rows"] == 3
    assert prof["invalid_values"]["orig_balance_inconsistent_total"] >= 1
    assert prof["target"]["positives"] == fixture_frame["isFraud"].sum()
    assert 0 < prof["target"]["prevalence"] < 0.1
    assert set(prof["target_by_type"]) == set(prof["type_values"])
    positive_types = {t for t, v in prof["target_by_type"].items() if v["positives"] > 0}
    assert positive_types <= {"TRANSFER", "CASH_OUT"}
    assert prof["steps"]["n_steps"] >= 10
    assert prof["steps"]["first_step_with_positive"] is not None
    assert prof["sensitive_attribute_prescan"]["any_match"] is False
    assert "isFlaggedFraud" in prof["rule_flag"]
    assert prof["identifiers"]["nameOrig"]["unique"] > 0


def test_profile_has_no_row_level_data(fixture_frame, schema) -> None:
    prof = profile_frame(fixture_frame, schema)
    text = json.dumps(prof)
    for ident in fixture_frame["nameOrig"].head(20):
        assert ident not in text


def test_run_profile_writes_reports_with_disclaimer(tmp_path: Path, fixture_frame, schema) -> None:
    md, js = run_profile(fixture_frame, schema, tmp_path, "fixture")
    text = md.read_text()
    assert DISCLAIMER in text
    for heading in [
        "Duplicates",
        "Invalid values",
        "Class imbalance",
        "Time steps",
        "Sensitive-attribute pre-scan",
        "Findings and handling decisions",
    ]:
        assert f"## {heading}" in text
    assert json.loads(js.read_text())["n_rows"] == len(fixture_frame)


def test_dictionary_without_profile_marks_ranges(tmp_path: Path, schema) -> None:
    out = build_dictionary(schema, tmp_path / "dd.md", registry_path=tmp_path / "none.yaml")
    text = out.read_text()
    assert "[PROFILE]" in text
    assert "No feature registry yet" in text
    assert DISCLAIMER in text
    assert "| nameOrig |" in text


def test_dictionary_uses_profile_and_registry(tmp_path: Path, fixture_frame, schema) -> None:
    _, js = run_profile(fixture_frame, schema, tmp_path, "fixture")
    reg = tmp_path / "features.yaml"
    reg.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "log_amount",
                    "source_columns": ["amount"],
                    "transform": "x",
                    "rationale": "heavy tail",
                    "available_at_prediction_time": "realtime",
                    "kind": "numeric",
                    "sets": ["primary"],
                    "dictionary_entry": {
                        "type": "float",
                        "unit": "log units",
                        "range_or_values": ">=0",
                        "description": "log1p(amount)",
                    },
                }
            ]
        )
    )
    out = build_dictionary(schema, tmp_path / "dd.md", registry_path=reg, profile_path=js)
    text = out.read_text()
    assert "[PROFILE]" not in text.split("## Engineered features")[0].split("## Raw variables")[1]
    assert "| log_amount |" in text and "Rationale: heavy tail" in text


def test_dictionary_rejects_feature_without_rationale(tmp_path: Path, schema) -> None:
    reg = tmp_path / "features.yaml"
    reg.write_text(yaml.safe_dump([{"name": "x", "dictionary_entry": {"type": "float"}}]))
    with pytest.raises(DictionaryError, match="rationale"):
        build_dictionary(schema, tmp_path / "dd.md", registry_path=reg)


@pytest.fixture
def fixture_config(tmp_path: Path, fixture_frame, repo_root: Path) -> Path:
    """A config that extends base.yaml but points at a fixture CSV and a temp reports dir."""
    csv = tmp_path / "fixture.csv"
    fixture_frame.to_csv(csv, index=False)
    cfg = tmp_path / "fixture.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {"raw_csv": str(csv), "reports_dir": str(tmp_path / "reports")},
            }
        )
    )
    return cfg


def test_cli_validate_profile_dictionary_end_to_end(
    fixture_config: Path, tmp_path: Path, capsys
) -> None:
    assert main(["validate-schema", "--config", str(fixture_config)]) == EXIT_OK
    assert "schema validation OK" in capsys.readouterr().out
    assert main(["profile", "--config", str(fixture_config)]) == EXIT_OK
    assert (tmp_path / "reports" / "data_quality.md").exists()
    assert main(["data-dictionary", "--config", str(fixture_config)]) == EXIT_OK
    dd = (tmp_path / "reports" / "data_dictionary.md").read_text()
    assert "[PROFILE]" not in dd.split("## Engineered features")[0].split("## Raw variables")[1]


def test_cli_validate_schema_fails_on_missing_column(
    fixture_config: Path, tmp_path: Path, fixture_frame
) -> None:
    csv = Path(yaml.safe_load(fixture_config.read_text())["paths"]["raw_csv"])
    fixture_frame.drop(columns=["type"]).to_csv(csv, index=False)
    assert main(["validate-schema", "--config", str(fixture_config)]) == EXIT_VALIDATION


def test_cli_requires_raw_csv(tmp_path: Path, repo_root: Path) -> None:
    cfg = tmp_path / "null_raw.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {"_extends": str(repo_root / "configs" / "base.yaml"), "paths": {"raw_csv": None}}
        )
    )
    with pytest.raises(SystemExit) as exc:
        main(["profile", "--config", str(cfg)])
    assert exc.value.code == EXIT_VALIDATION


def test_balance_check_is_direction_aware(fixture_frame, schema) -> None:
    """A CASH_IN row whose balance rises by exactly the amount is consistent."""
    df = fixture_frame.copy()
    cash_in = df.index[df["type"] == "CASH_IN"][:5]
    df.loc[cash_in, "newbalanceOrig"] = df.loc[cash_in, "oldbalanceOrg"] + df.loc[cash_in, "amount"]
    prof = profile_frame(df, schema)
    assert prof["invalid_values"]["by_type"]["CASH_IN"]["orig_inconsistent"] < len(
        df[df["type"] == "CASH_IN"]
    )


def test_narrative_file_is_included_and_survives_regeneration(
    tmp_path: Path, fixture_frame, schema
) -> None:
    narrative = tmp_path / "data_quality_narrative.md"
    narrative.write_text(
        "## Findings and handling decisions\n\n| ID | x |\n|---|---|\n| DQ-01 | keep |\n\n## Source-data limitations\n\n- synthetic\n"
    )
    md, _ = run_profile(fixture_frame, schema, tmp_path, "fixture")
    text = md.read_text()
    assert "DQ-01" in text and "## Source-data limitations" in text
    md, _ = run_profile(fixture_frame, schema, tmp_path, "fixture")  # regenerate
    assert "DQ-01" in md.read_text()
