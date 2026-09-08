"""Batch Transaction-Risk Triage UI (specs/002-batch-triage-ui). Run: `make ui` (needs `make api`).

Session state machine (data-model §8): empty -> loaded (rows) -> scored (result) -> empty. Everything
lives in ``st.session_state`` (process memory); nothing is written to disk, cached, or logged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from aml_triage.ui import export, texts, views
from aml_triage.ui.client import (
    BadRequest,
    BatchTooLarge,
    HttpTriageClient,
    ServiceUnavailable,
    load_ui_config,
)
from aml_triage.ui.inputs import StructuralError, parse_manual_rows, read_csv_rows

STATE_KEYS = ("rows", "source", "result", "error", "explanations", "selected_row", "ignore_upload")


def _init_state() -> None:
    for key in STATE_KEYS:
        st.session_state.setdefault(key, None)
    st.session_state.setdefault("ui_config", load_ui_config())
    if st.session_state.get("client") is None:
        st.session_state["client"] = HttpTriageClient.from_config()


def _clear() -> None:
    for key in STATE_KEYS:
        st.session_state[key] = None


def _structural_message(exc: StructuralError, limit: int) -> str:
    if exc.kind == "unknown_columns":
        return texts.UNKNOWN_COLUMNS.format(cols=", ".join(exc.detail.get("cols", [])))
    if exc.kind == "missing_columns":
        return texts.UNKNOWN_COLUMNS.format(cols="missing " + ", ".join(exc.detail.get("cols", [])))
    if exc.kind == "empty":
        return texts.EMPTY_FILE
    if exc.kind == "over_limit":
        return texts.OVER_LIMIT.format(n=exc.detail.get("n"), limit=exc.detail.get("limit", limit))
    return texts.UNREADABLE


def _load_rows(rows: list[dict[str, Any]], source: str) -> None:
    st.session_state["rows"] = rows
    st.session_state["source"] = source
    st.session_state["result"] = None
    st.session_state["explanations"] = None
    st.session_state["selected_row"] = None
    st.session_state["error"] = None


def _handle_upload(uploaded: Any, limit: int) -> None:
    signature = (uploaded.name, uploaded.size)
    if st.session_state.get("ignore_upload") == signature:
        return
    if st.session_state.get("source") == f"upload:{uploaded.name}" and st.session_state.get("rows"):
        return
    try:
        rows = read_csv_rows(uploaded.getvalue(), limit)
    except StructuralError as exc:
        st.session_state["rows"] = None
        st.session_state["result"] = None
        st.session_state["error"] = _structural_message(exc, limit)
        st.session_state["ignore_upload"] = signature
        return
    _load_rows(rows, f"upload:{uploaded.name}")


def _load_example(limit: int) -> None:
    path = Path(st.session_state["ui_config"].get("example_batch", ""))
    if not path.exists():
        st.session_state["error"] = texts.UNREADABLE
        return
    rows = read_csv_rows(path.read_bytes(), limit)
    _load_rows(rows, f"example:{path.name}")
    st.session_state["example_loaded"] = (len(rows), str(path))


def _score(limit: int) -> None:
    client = st.session_state["client"]
    explain = st.session_state["ui_config"].get("explain_default", "high")
    try:
        st.session_state["result"] = client.score_batch(st.session_state["rows"], explain)
        st.session_state["explanations"] = {}
        st.session_state["error"] = None
    except BatchTooLarge as exc:
        st.session_state["error"] = texts.BATCH_TOO_LARGE.format(detail=exc.detail)
    except BadRequest as exc:
        st.session_state["error"] = texts.BAD_REQUEST.format(detail=exc.detail)
    except ServiceUnavailable as exc:
        st.session_state["error"] = texts.SERVICE_DOWN.format(url=exc.url)


def main() -> None:
    st.set_page_config(page_title=texts.TITLE, layout="wide")
    _init_state()
    client = st.session_state["client"]
    try:
        cfg = client.config()
    except ServiceUnavailable:
        cfg = None
    views.sidebar(cfg, client.base_url)
    st.title(texts.TITLE)
    st.markdown(texts.PURPOSE)
    if cfg is None:
        st.error(texts.SERVICE_DOWN.format(url=client.base_url))
        views.footer()
        st.stop()
    limit = int(cfg["batch_limit"])

    tab_upload, tab_manual = st.tabs([texts.TAB_UPLOAD, texts.TAB_MANUAL])
    with tab_upload:
        st.caption(texts.EXPECTED_COLUMNS)
        st.caption(texts.SIDEBAR_LIMIT.format(limit=limit))
        uploaded = st.file_uploader(texts.TAB_UPLOAD, type=["csv"], key="uploader")
        st.caption(texts.PRIVACY_NOTE)
        if st.button(texts.BTN_EXAMPLE, key="example"):
            _load_example(limit)
        if uploaded is not None:
            _handle_upload(uploaded, limit)
    with tab_manual:
        st.caption(texts.EXPECTED_COLUMNS)
        text = st.text_area(texts.TAB_MANUAL, key="manual_text", height=160)
        if st.button("Use these rows", key="use_manual"):
            try:
                _load_rows(parse_manual_rows(text or "", limit), "manual entry")
            except StructuralError as exc:
                st.session_state["rows"] = None
                st.session_state["result"] = None
                st.session_state["error"] = _structural_message(exc, limit)

    # Demo mode for screenshots/docs: `?demo=example` loads and scores the bundled synthetic example
    # once; it uses exactly the same path as pressing the two buttons.
    if (
        st.query_params.get("demo") == "example"
        and not st.session_state.get("rows")
        and not st.session_state.get("demo_done")
    ):
        _load_example(limit)
        if st.session_state.get("rows"):
            _score(limit)
        st.session_state["demo_done"] = True

    if st.session_state.get("error"):
        st.error(st.session_state["error"])

    rows = st.session_state.get("rows")
    result = st.session_state.get("result")
    if rows and result is None:
        source = st.session_state.get("source") or "input"
        if source.startswith("example:"):
            n, path = st.session_state.get("example_loaded", (len(rows), source))
            st.markdown(texts.EXAMPLE_LABEL.format(n=n, path=path))
        st.markdown(texts.LOADED.format(n=len(rows), source=source, btn=texts.BTN_SCORE))
        if st.button(texts.BTN_SCORE, key="score", type="primary"):
            _score(limit)
            result = st.session_state.get("result")
            if st.session_state.get("error"):
                st.error(st.session_state["error"])

    if rows and result is not None:
        views.summary(result)
        views.rule_text(result)
        views.duplicates_note(rows)
        views.queue_table(rows, result)
        views.validation_report(result)
        views.explanation_panel(rows, result, client)
        queue_name, skipped_name = export.file_names(result["model_version"])
        c1, c2 = st.columns(2)
        c1.download_button(
            texts.BTN_DOWNLOAD_QUEUE,
            data=export.queue_csv(rows, result),
            file_name=queue_name,
            mime="text/csv",
            key="dl_queue",
        )
        if result.get("skipped"):
            c2.download_button(
                texts.BTN_DOWNLOAD_SKIPPED,
                data=export.skipped_csv(rows, result),
                file_name=skipped_name,
                mime="text/csv",
                key="dl_skipped",
            )

    if rows and st.button(texts.BTN_CLEAR, key="clear"):
        _clear()
        st.rerun()

    views.footer()


if __name__ == "__main__":  # `streamlit run` and AppTest execute this file as __main__
    main()
