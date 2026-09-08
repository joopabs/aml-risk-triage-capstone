"""Constitution Principle XI: the core package must import and run with the optional API absent."""

from __future__ import annotations

import importlib
import pkgutil
import sys

import pytest


def test_core_modules_import_with_api_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "aml_triage.api", None)  # makes `import aml_triage.api` fail
    for name in [
        m
        for m in list(sys.modules)
        if m.startswith("aml_triage.") and not m.startswith("aml_triage.api")
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    import aml_triage

    imported: list[str] = []
    for mod in pkgutil.walk_packages(aml_triage.__path__, prefix="aml_triage."):
        if mod.name.startswith(("aml_triage.api", "aml_triage.ui")) or mod.name.endswith(
            "__main__"
        ):
            continue  # both optional components are excluded from the core import walk
        importlib.import_module(mod.name)
        imported.append(mod.name)
    assert "aml_triage.cli" in imported
    assert "aml_triage.config" in imported
    with pytest.raises(ImportError):
        importlib.import_module("aml_triage.api")


def test_core_modules_never_import_the_optional_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Feature 002: `aml_triage.ui` (and Streamlit) must not be a dependency of any core module."""
    monkeypatch.setitem(sys.modules, "aml_triage.ui", None)
    monkeypatch.setitem(sys.modules, "streamlit", None)
    for name in [
        m
        for m in list(sys.modules)
        if m.startswith("aml_triage.") and not m.startswith(("aml_triage.api", "aml_triage.ui"))
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    import aml_triage

    for mod in pkgutil.walk_packages(aml_triage.__path__, prefix="aml_triage."):
        if mod.name.startswith(("aml_triage.api", "aml_triage.ui")) or mod.name.endswith(
            "__main__"
        ):
            continue
        importlib.import_module(mod.name)
    from aml_triage.cli import main

    with pytest.raises(SystemExit):
        main(["--help"])
    assert sys.modules.get("streamlit") is None
    assert sys.modules.get("aml_triage.ui") is None
    with pytest.raises(ImportError):
        importlib.import_module("aml_triage.ui")
