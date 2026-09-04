from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aml_triage.cli import COMMANDS, build_parser, main
from aml_triage.constants import EXIT_ERROR, EXIT_OK, EXIT_VALIDATION

CONTRACT_COMMANDS = {
    "fetch-data", "validate-schema", "profile", "data-dictionary", "split", "build-features",
    "eda", "select-features", "pca", "train", "compare", "tune", "choose-operating-point",
    "freeze", "evaluate", "select", "reproduce-check", "explain", "fairness-availability",
    "fairness", "build-report", "queue",
}  # fmt: skip


def test_all_contract_commands_registered() -> None:
    names = {c[0] for c in COMMANDS}
    assert names == CONTRACT_COMMANDS
    assert len(names) == 22


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for name in CONTRACT_COMMANDS:
        assert name in out


def test_no_command_prints_help_and_exits_0() -> None:
    assert main([]) == EXIT_OK


def test_stub_exits_1_with_message(
    capsys: pytest.CaptureFixture[str], base_config_path: Path
) -> None:
    rc = main(["reproduce-check", "--config", str(base_config_path)])
    assert rc == EXIT_ERROR
    assert "not implemented" in capsys.readouterr().err


def test_missing_config_exits_2(tmp_path: Path) -> None:
    assert main(["reproduce-check", "--config", str(tmp_path / "missing.yaml")]) == EXIT_VALIDATION


def test_seed_override_reaches_config(
    base_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["reproduce-check", "--config", str(base_config_path), "--seed", "9"])
    assert "seed=9" in capsys.readouterr().err


def test_module_entry_point(base_config_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "aml_triage", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.startswith("aml_triage ")


def test_command_specific_options_parse() -> None:
    p = build_parser()
    a = p.parse_args(["evaluate", "--split", "test", "--force-reevaluate", "--reason", "x"])
    assert a.split == "test" and a.force_reevaluate and a.reason == "x"
    assert p.parse_args(["queue", "--period", "3"]).period == 3
    assert p.parse_args(["build-features", "--feature-set", "primary"]).feature_set == "primary"
