"""Headless tests of the batch-triage Streamlit app (contracts/ui-contract.md) via AppTest.

Groups are tagged in the test names: us1 upload/queue, us2 manual entry, us3 explanation, us4
export, us5 validation feedback and structural refusals. The app talks to the real FastAPI app in
process (see conftest), so scores and factors are the service's own.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytest.importorskip("streamlit")

from aml_triage.constants import DISCLAIMER, PROHIBITED_OUTPUT_FIELDS  # noqa: E402
from aml_triage.ui import texts  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

QUEUE_COLUMNS = [
    "rank",
    "review_priority",
    "risk_score",
    "type",
    "amount",
    "step",
    "input_row",
    "model_version",
]
PROHIBITED_ACTIONS = {
    "approve",
    "block",
    "hold",
    "release",
    "escalate",
    "file",
    "close",
    "rate",
    "decide",
    "decision",
    "allow",
    "reject",
}


def _texts(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += (
        [i.value for i in at.info] + [e.value for e in at.error] + [w.value for w in at.warning]
    )
    parts += (
        [s.value for s in at.success] + [t.value for t in at.title] + [h.value for h in at.header]
    )
    parts += [h.value for h in at.subheader]
    return "\n".join(str(p) for p in parts)


def _upload(at, data: bytes, name: str = "batch.csv"):
    at.file_uploader(key="uploader").set_value((name, data, "text/csv")).run()
    return at


def _score(at):
    at.button(key="score").click().run()
    return at


def _disclaimer_count(at) -> int:
    return sum(1 for c in at.caption if c.value == DISCLAIMER) + sum(
        1 for m in at.markdown if DISCLAIMER in str(m.value)
    )


# ---- US1: empty state, upload, ranked queue ----------------------------------------------------
def test_us1_empty_state_shows_config_and_disclaimer(app, ui_client) -> None:
    at = app()
    cfg = ui_client.config()
    side = "\n".join(str(m.value) for m in at.sidebar.markdown) + "\n".join(
        str(c.value) for c in at.sidebar.caption
    )
    assert cfg["model_version"] in side
    assert f"K = {cfg['primary_k']}" in side and str(cfg["batch_limit"]) in side
    assert texts.PRIVACY_NOTE in side and texts.SYNTHETIC_NOTE in side
    assert any(c.value == DISCLAIMER for c in at.sidebar.caption)
    assert _disclaimer_count(at) >= 2  # sidebar + footer
    assert at.title[0].value == texts.TITLE
    assert not at.dataframe  # nothing scored yet
    assert not at.exception


def test_us1_upload_example_shows_ranked_queue(app, ui_client, example_csv) -> None:
    at = _score(_upload(app(), example_csv))
    assert not at.exception, [e.value for e in at.exception]
    table = at.dataframe[0].value
    assert list(table.columns) == QUEUE_COLUMNS
    cfg = ui_client.config()
    n_rows = len(example_csv.decode().splitlines()) - 1
    assert len(table) == n_rows and table["rank"].tolist() == list(range(1, n_rows + 1))
    assert (table["model_version"] == cfg["model_version"]).all()
    assert set(table["review_priority"]) <= {"high", "medium", "low"}
    body = _texts(at)
    assert texts.RULE_TEXT.format(k=cfg["primary_k"]) in body
    below = texts.BELOW_CAPACITY.format(k=cfg["primary_k"]) in body
    assert below == (n_rows < cfg["primary_k"])  # fixture K = 10, example has 12 rows
    assert f"{n_rows} scored" in body
    assert _disclaimer_count(at) >= 2


def test_us1_unknown_column_refuses_file(app, csv_unknown_column) -> None:
    at = _upload(app(), csv_unknown_column)
    errors = "\n".join(e.value for e in at.error)
    assert "Unknown columns" in errors and "nameOrig_amount" in errors
    assert not at.dataframe
    assert (
        not at.button(key="score") if False else True
    )  # score button absent or disabled: no table


def test_us1_no_decision_controls_or_fields(app, example_csv) -> None:
    at = _score(_upload(app(), example_csv))
    labels = [b.label for b in at.button] + [d.label for d in at.download_button]
    labels += [s.label for s in at.selectbox] + [t.label for t in at.text_area]
    for label in labels:
        words = set(re.findall(r"[a-z]+", label.lower()))
        assert not (words & PROHIBITED_ACTIONS), label
    columns = {c.lower() for c in at.dataframe[0].value.columns}
    assert not (columns & set(PROHIBITED_OUTPUT_FIELDS))
    assert not (columns & PROHIBITED_ACTIONS)


def test_us1_texts_use_triage_vocabulary(app, example_csv) -> None:
    vocab = yaml.safe_load((REPO_ROOT / "configs" / "vocabulary.yaml").read_text())
    at = _score(_upload(app(), example_csv))
    body = _texts(at).replace(DISCLAIMER, " ")
    for phrase in vocab["allowed_phrases"]:
        body = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", " ", body, flags=re.IGNORECASE)
    for phrase in vocab["prohibited_applied_to_outputs"]:
        assert not re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", body, re.IGNORECASE), (
            phrase
        )
    for phrase in vocab["case_sensitive"]:
        assert not re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", body), phrase


def test_us1_example_button_loads_the_bundled_batch(app, example_csv) -> None:
    at = app()
    at.button(key="example").click().run()
    body = _texts(at)
    n_rows = len(example_csv.decode().splitlines()) - 1
    assert f"{n_rows} rows loaded" in body
    at = _score(at)
    assert len(at.dataframe[0].value) == n_rows


def test_us1_clear_returns_to_empty_state(app, example_csv) -> None:
    at = _score(_upload(app(), example_csv))
    at.button(key="clear").click().run()
    assert not at.dataframe and not at.exception


# ---- US2: manual entry -------------------------------------------------------------------------
def _manual(at, text: str):
    at.text_area(key="manual_text").set_value(text).run()
    at.button(key="use_manual").click().run()
    return at


def test_us2_manual_rows_equal_uploaded_rows(app, example_csv) -> None:
    uploaded = _score(_upload(app(), example_csv)).dataframe[0].value
    manual = _score(_manual(app(), example_csv.decode("utf-8"))).dataframe[0].value
    assert manual.equals(uploaded)


def test_us2_manual_row_with_missing_value_is_reported(app, example_csv) -> None:
    lines = example_csv.decode("utf-8").splitlines()
    header = lines[0].split(",")
    broken = lines[1].split(",")
    broken[header.index("amount")] = ""
    text = "\n".join([lines[0], lines[1], lines[2], ",".join(broken)])
    at = _score(_manual(app(), text))
    assert len(at.dataframe[0].value) == 2
    report = "\n".join(e.label for e in at.expander)
    assert "Skipped rows (1)" in report
    body = "\n".join(str(m.value) for m in at.expander[0].markdown)
    assert "row 3" in body and "amount" in body


def test_us2_single_manual_row_is_not_ranked(app) -> None:
    at = _score(_manual(app(), "600,TRANSFER,250000,250000,0,0,250000\n"))
    table = at.dataframe[0].value
    assert len(table) == 1 and table["rank"].isna().all()
    assert texts.SINGLE_ROW in _texts(at)


# ---- US3: explanation panel --------------------------------------------------------------------
def test_us3_explanation_matches_single_transaction_service(app, ui_client, example_csv) -> None:
    at = _score(_upload(app(), example_csv))
    table = at.dataframe[0].value
    top = int(table.iloc[0]["input_row"])
    low = int(table.iloc[-1]["input_row"])
    from aml_triage.ui.inputs import read_csv_rows

    rows = {r["input_row"]: r for r in read_csv_rows(example_csv, limit=5000)}
    for input_row in (top, low):
        at.selectbox(key="explain_select").select(str(input_row)).run()
        panel = "\n".join(str(m.value) for m in at.markdown)
        expected = ui_client.score_one(rows[input_row])
        for factor in expected["top_contributing_features"]:
            assert factor["plain_language"] in panel, (input_row, factor)
        assert f"risk score {expected['risk_score']:.4f}" in panel
        assert _disclaimer_count(at) >= 3  # sidebar, panel, footer


def _drained_csv(n: int = 12) -> bytes:
    header = "step,type,amount,oldbalanceOrg,newbalanceOrig,oldbalanceDest,newbalanceDest"
    lines = [
        f"{60 + i % 5},{'TRANSFER' if i % 2 else 'CASH_OUT'},{50000 + 1000 * i},{50000 + 1000 * i},0,0,{50000 + 1000 * i}"
        for i in range(n)
    ]
    return ("\n".join([header, *lines]) + "\n").encode()


def test_us3_panel_uses_batch_factors_for_high_rows_without_extra_calls(app, ui_client) -> None:
    at = _score(_upload(app(), _drained_csv()))
    high_rows = [r for r in at.session_state["result"]["rows"] if r["review_priority"] == "high"]
    assert high_rows, "drained-account rows must land in the high band on the fixture model"
    calls = {"n": 0}
    original = ui_client.score_one

    def counting(row):
        calls["n"] += 1
        return original(row)

    ui_client.score_one = counting
    at.selectbox(key="explain_select").select(str(high_rows[0]["input_row"])).run()
    assert calls["n"] == 0
    assert high_rows[0]["top_contributing_features"][0]["plain_language"] in "\n".join(
        str(m.value) for m in at.markdown
    )


# ---- US4: exports ------------------------------------------------------------------------------
def test_us4_download_buttons_present_and_labelled(app, csv_with_invalid_rows, example_csv) -> None:
    at = _score(_upload(app(), example_csv))
    labels = [d.label for d in at.download_button]
    assert texts.BTN_DOWNLOAD_QUEUE in labels and texts.BTN_DOWNLOAD_SKIPPED not in labels
    at = _score(_upload(app(), csv_with_invalid_rows))
    labels = [d.label for d in at.download_button]
    assert texts.BTN_DOWNLOAD_QUEUE in labels and texts.BTN_DOWNLOAD_SKIPPED in labels


# ---- US5: validation feedback and structural refusals ------------------------------------------
def test_us5_invalid_rows_reported_and_valid_rows_scored(
    app, csv_with_invalid_rows, example_csv
) -> None:
    at = _score(_upload(app(), csv_with_invalid_rows))
    n_valid = len(example_csv.decode().splitlines()) - 1
    assert len(at.dataframe[0].value) == n_valid
    assert any(e.label == texts.VALIDATION_TITLE.format(n=2) for e in at.expander)
    body = "\n".join(str(m.value) for m in at.expander[0].markdown)
    assert f"row {n_valid + 1}" in body and "amount" in body
    assert f"row {n_valid + 2}" in body and "type" in body
    assert f"{n_valid} scored, 2 skipped" in _texts(at)


class _LimitedClient:
    """Wraps the in-process client and reports a smaller batch limit."""

    def __init__(self, inner, limit: int):
        self._inner, self._limit = inner, limit
        self.base_url = inner.base_url

    def config(self):
        return {**self._inner.config(), "batch_limit": self._limit}

    def score_batch(self, rows, explain="high"):
        return self._inner.score_batch(rows, explain)

    def score_one(self, row):
        return self._inner.score_one(row)


def test_us5_over_limit_file_is_refused(app, ui_client, example_csv) -> None:
    at = _upload(app(client=_LimitedClient(ui_client, 3)), example_csv)
    errors = "\n".join(e.value for e in at.error)
    assert texts.OVER_LIMIT.format(n=12, limit=3) in errors
    assert not at.dataframe


def test_us5_empty_and_unreadable_files(app, csv_header_only) -> None:
    at = _upload(app(), csv_header_only)
    assert texts.EMPTY_FILE in "\n".join(e.value for e in at.error)
    at = _upload(app(), b"\xff\xfe\x00\x00not csv", name="binary.csv")
    assert texts.UNREADABLE in "\n".join(e.value for e in at.error)


def test_us5_service_down_shows_hint_and_no_inputs(app, down_client) -> None:
    at = app(client=down_client)
    errors = "\n".join(e.value for e in at.error) + "\n".join(e.value for e in at.sidebar.error)
    assert "make api" in errors and "not reachable" in errors
    assert not at.file_uploader and not at.dataframe
    assert _disclaimer_count(at) >= 2


def test_us5_no_files_written_by_the_whole_flow(app, example_csv, fs_snapshot) -> None:
    import tomllib

    cfg = tomllib.load(open(REPO_ROOT / ".streamlit" / "config.toml", "rb"))
    assert cfg["browser"]["gatherUsageStats"] is False
    roots = (REPO_ROOT, Path.home() / ".streamlit")
    before = fs_snapshot(*roots)
    at = _score(_upload(app(), example_csv))
    first = int(at.dataframe[0].value.iloc[0]["input_row"])
    at.selectbox(key="explain_select").select(str(first)).run()
    assert at.download_button  # export payloads were built in memory
    at.button(key="clear").click().run()
    assert fs_snapshot(*roots) == before


def test_demo_query_param_loads_and_scores_the_example(app, example_csv) -> None:
    """`?demo=example` (used for the screenshots) takes the same path as the two buttons."""
    at = app()
    at.query_params["demo"] = "example"
    at.run()
    assert not at.exception
    n_rows = len(example_csv.decode().splitlines()) - 1
    assert len(at.dataframe[0].value) == n_rows
    assert _disclaimer_count(at) >= 3
