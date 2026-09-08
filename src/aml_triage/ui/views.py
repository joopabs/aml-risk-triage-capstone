"""Render helpers for the batch-triage UI (contracts/ui-contract.md). Every string comes from texts.py."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from aml_triage.constants import DISCLAIMER
from aml_triage.ui import texts
from aml_triage.ui.inputs import rows_frame

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


def sidebar(cfg: dict[str, Any] | None, url: str) -> None:
    with st.sidebar:
        st.markdown(f"**{texts.SIDEBAR_STATUS}**")
        if cfg is None:
            st.error(texts.SERVICE_DOWN.format(url=url))
        else:
            st.markdown(texts.SIDEBAR_REACHABLE.format(url=url))
            st.markdown(texts.SIDEBAR_MODEL.format(version=cfg["model_version"]))
            st.markdown(
                texts.SIDEBAR_OP.format(k=cfg["primary_k"], threshold=f"{cfg['threshold']:.6f}")
            )
            st.markdown(texts.SIDEBAR_LIMIT.format(limit=cfg["batch_limit"]))
        st.divider()
        st.caption(texts.SYNTHETIC_NOTE)
        st.caption(texts.PRIVACY_NOTE)
        st.caption(DISCLAIMER)


def summary(result: dict[str, Any]) -> None:
    c = result["counts"]
    st.markdown(
        texts.SUMMARY.format(
            received=c["received"],
            scored=c["scored"],
            skipped=c["skipped"],
            high=c["high"],
            medium=c["medium"],
            low=c["low"],
            version=result["model_version"],
        )
    )


def rule_text(result: dict[str, Any]) -> None:
    k = int(result["operating_point"]["primary_k"])
    st.markdown(texts.RULE_TEXT.format(k=k))
    scored = int(result["counts"]["scored"])
    if scored == 1 and not result["ranked"]:
        st.info(texts.SINGLE_ROW)
    elif scored < k:
        st.info(texts.BELOW_CAPACITY.format(k=k))


def queue_frame(rows_in: list[dict[str, Any]], result: dict[str, Any]) -> pd.DataFrame:
    """Scored rows joined to their inputs on input_row, in rank order, queue columns only."""
    inputs = rows_frame(rows_in).set_index("input_row")
    scored = pd.DataFrame(result["rows"])
    if scored.empty:
        return pd.DataFrame(columns=QUEUE_COLUMNS)
    scored = scored.set_index("input_row")
    joined = scored.join(inputs[["type", "amount", "step"]], how="left")
    joined["model_version"] = result["model_version"]
    joined = joined.reset_index()
    joined["rank"] = joined["rank"].astype("Int64")
    return (
        joined[QUEUE_COLUMNS]
        .sort_values(["rank", "input_row"], na_position="last", kind="mergesort")
        .reset_index(drop=True)
    )


def queue_table(rows_in: list[dict[str, Any]], result: dict[str, Any]) -> pd.DataFrame:
    st.subheader(texts.QUEUE_TITLE)
    df = queue_frame(rows_in, result)
    st.dataframe(df, hide_index=True, width="stretch", key="queue")
    return df


def validation_report(result: dict[str, Any]) -> None:
    issues = result.get("skipped") or []
    if not issues:
        return
    n_rows = len({i["input_row"] for i in issues})
    with st.expander(texts.VALIDATION_TITLE.format(n=n_rows), expanded=False):
        st.markdown(
            "\n".join(
                "- "
                + texts.VALIDATION_LINE.format(
                    input_row=i["input_row"], field=i["field"], reason=i["reason"]
                )
                for i in issues
            )
        )


def duplicates_note(rows_in: list[dict[str, Any]]) -> None:
    keys = [tuple((k, str(v)) for k, v in sorted(r.items()) if k != "input_row") for r in rows_in]
    n_dup = len(keys) - len(set(keys))
    if n_dup:
        st.caption(texts.DUPLICATES.format(n=n_dup))


def explanation_panel(rows_in: list[dict[str, Any]], result: dict[str, Any], client: Any) -> None:
    """Factors for one selected row: from the batch response when present, else via the single path."""
    scored = {r["input_row"]: r for r in result["rows"]}
    if not scored:
        return
    st.subheader(texts.EXPLAIN_TITLE)
    options = [str(r["input_row"]) for r in result["rows"]]
    choice = st.selectbox(texts.EXPLAIN_SELECT, options, key="explain_select")
    input_row = int(choice)
    row = scored[input_row]
    factors = row.get("top_contributing_features") or []
    cache = st.session_state.setdefault("explanations", {}) or {}
    if not factors:
        if input_row not in cache:
            src = next(r for r in rows_in if r["input_row"] == input_row)
            cache[input_row] = client.score_one(src).get("top_contributing_features", [])
            st.session_state["explanations"] = cache
        factors = cache[input_row]
    rank = row["rank"] if row.get("rank") is not None else texts.NOT_RANKED
    st.markdown(
        texts.EXPLAIN_HEADER.format(
            rank=rank,
            priority=row["review_priority"],
            score=float(row["risk_score"]),
            version=result["model_version"],
        )
    )
    if factors:
        st.markdown("\n".join(f"- {f['plain_language']}" for f in factors))
    else:
        st.markdown(texts.EXPLAIN_NONE)
    st.caption(DISCLAIMER)


def footer() -> None:
    st.divider()
    st.caption(DISCLAIMER)
