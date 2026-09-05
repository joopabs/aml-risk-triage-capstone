"""FR-084 / constitution Principle IX: no determination language applied to model outputs,
and the disclaimer on every report surface."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from aml_triage.constants import DISCLAIMER

VOCAB_PATH = Path(__file__).resolve().parents[1] / "configs" / "vocabulary.yaml"


def _load_vocab() -> dict:
    with open(VOCAB_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _phrase_re(phrase: str, case_sensitive: bool = False) -> re.Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", flags)


def _strip_allowed(text: str, vocab: dict) -> str:
    text = text.replace(DISCLAIMER, " ")
    for phrase in vocab.get("allowed_phrases", []):
        text = _phrase_re(phrase).sub(" ", text)
    return text


def find_prohibited(text: str, vocab: dict) -> list[str]:
    cleaned = _strip_allowed(text, vocab)
    hits: list[str] = []
    for phrase in vocab.get("prohibited_applied_to_outputs", []):
        if _phrase_re(phrase).search(cleaned):
            hits.append(phrase)
    for phrase in vocab.get("case_sensitive", []):
        if _phrase_re(phrase, case_sensitive=True).search(cleaned):
            hits.append(phrase)
    return hits


def _read_text(path: Path) -> str:
    if path.suffix == ".ipynb":
        nb = json.loads(path.read_text(encoding="utf-8"))
        return "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []))
    return path.read_text(encoding="utf-8", errors="ignore")


def _scan_files(repo_root: Path, vocab: dict) -> list[Path]:
    exts = set(vocab.get("scan_extensions", [".py", ".md", ".ipynb", ".txt"]))
    files: list[Path] = []
    for rel in vocab["scan_paths"]:
        p = repo_root / rel
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(
                f
                for f in p.rglob("*")
                if f.is_file() and f.suffix in exts and "__pycache__" not in f.parts
            )
    return files


def test_vocabulary_config_is_well_formed() -> None:
    vocab = _load_vocab()
    assert vocab["required_literal"] == "operational error-slice analysis"
    assert vocab["prohibited_applied_to_outputs"]
    assert "README.md" in vocab["scan_paths"]


def test_detector_self_check() -> None:
    vocab = _load_vocab()
    assert find_prohibited("The model says this is a fraudulent transaction.", vocab) == [
        "fraudulent transaction"
    ]
    assert (
        find_prohibited("Label 1 means simulated fraud; no automatic blocking occurs.", vocab) == []
    )
    assert find_prohibited("The investigator may file a SAR.", vocab) == ["SAR"]
    assert find_prohibited("necessary sarcasm", vocab) == []
    assert find_prohibited(DISCLAIMER, vocab) == []


def test_no_prohibited_language_in_scan_paths(repo_root: Path) -> None:
    vocab = _load_vocab()
    offenders: dict[str, list[str]] = {}
    for f in _scan_files(repo_root, vocab):
        hits = find_prohibited(_read_text(f), vocab)
        if hits:
            offenders[str(f.relative_to(repo_root))] = hits
    assert not offenders, f"prohibited determination language found: {offenders}"


def test_disclaimer_present_in_every_report(repo_root: Path) -> None:
    reports = [
        p
        for p in (repo_root / "reports").rglob("*.md")
        if p.is_file() and not p.name.endswith("_narrative.md") and "sections" not in p.parts
    ]  # narrative/section files are embedded into a report that carries the footer
    if not reports:
        pytest.skip("no report files yet")
    missing = [str(p.relative_to(repo_root)) for p in reports if DISCLAIMER not in p.read_text()]
    assert not missing, f"reports without the disclaimer: {missing}"


def test_fairness_labeling_rules(repo_root: Path) -> None:
    """When no valid sensitive-group labels exist, the fairness report must carry the literal
    slice label and none of the forbidden protected-group claims (spec FR-072/FR-073)."""
    vocab = _load_vocab()
    availability = repo_root / "reports" / "fairness_availability.json"
    report = repo_root / "reports" / "bias_fairness_analysis.md"
    if not (availability.exists() and report.exists()):
        pytest.skip("fairness artifacts not generated yet (Milestone M7)")
    record = json.loads(availability.read_text())
    text = report.read_text()
    if record.get("any_valid_label") is False:
        assert vocab["required_literal"] in text.lower()
        for phrase in vocab["fairness_forbidden_when_unavailable"]:
            assert not _phrase_re(phrase).search(text), f"forbidden fairness claim: {phrase}"


def test_fairness_report_heading_order_and_mislabel_detection(tmp_path: Path) -> None:
    """The six headings must appear in contract order; a mislabelled slice section must fail."""
    from aml_triage.fairness.report import HEADINGS, NON_MEASURABLE

    vocab = _load_vocab()
    good = "# Bias & Fairness Analysis\n\n" + "\n\n".join(f"## {h}\n\ntext" for h in HEADINGS)
    good = good.replace(
        "## Demographic Fairness\n\ntext", f"## Demographic Fairness\n\n{NON_MEASURABLE}"
    )
    good = good.replace(
        "## Operational Error-Slice Analysis\n\ntext",
        "## Operational Error-Slice Analysis\n\nLabel: operational error-slice analysis.",
    )
    positions = [good.index(f"## {h}") for h in HEADINGS]
    assert positions == sorted(positions)
    assert vocab["required_literal"] in good.lower()
    bad = re.sub(
        r"operational error-slice analysis",
        "demographic fairness result by transaction type",
        good,
        flags=re.IGNORECASE,
    )
    assert any(_phrase_re(p).search(bad) for p in vocab["fairness_forbidden_when_unavailable"])
    assert vocab["required_literal"] not in bad.lower()
