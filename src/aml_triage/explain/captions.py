"""Plain-language captions for explanations (spec FR-061/FR-063). Never determination language."""

from __future__ import annotations

from aml_triage.constants import DISCLAIMER
from aml_triage.features.base import FeatureDef

HUMAN_NAMES = {
    "log_amount": "transaction amount (log scale)",
    "amount_bucket": "amount decile",
    "log_oldbalance_org": "origin balance before the transaction (log scale)",
    "log_oldbalance_dest": "destination balance before the transaction (log scale)",
    "amount_to_orig_balance_ratio": "amount relative to the origin balance",
    "orig_zero_balance_flag": "origin balance was zero before",
    "dest_zero_balance_flag": "destination balance was zero before",
    "zero_amount_flag": "zero-amount transaction",
    "dest_is_merchant": "destination is a merchant account",
    "step_hour_of_day": "hour of the simulated day",
    "orig_balance_delta": "posted change in origin balance",
    "dest_balance_delta": "posted change in destination balance",
    "orig_balance_inconsistent_flag": "origin balance arithmetic does not reconcile",
    "dest_balance_inconsistent_flag": "destination balance arithmetic does not reconcile",
    "orig_zero_after_flag": "origin account emptied to zero",
    "orig_prior_txn_count": "earlier transactions by the same origin",
    "orig_prior_amount_sum": "earlier outflow by the same origin",
    "dest_prior_txn_count": "earlier transactions to the same destination",
    "dest_prior_amount_sum": "earlier inflow to the same destination",
}


def human_name(feature: str) -> str:
    if feature.startswith("type_"):
        return f"transaction type is {feature[5:]}"
    return HUMAN_NAMES.get(feature, feature.replace("_", " "))


def direction_phrase(contribution: float) -> str:
    return "raised" if contribution > 0 else "lowered"


def local_caption(
    contribs: list[tuple[str, float, float]],
    score: float,
    rank: int,
    period_label: str,
    units: str = "log-odds",
) -> str:
    """``contribs``: list of (feature, value, contribution) sorted by |contribution| desc."""
    parts = []
    for feat, value, c in contribs:
        v = (
            f"{value:,.2f}"
            if isinstance(value, float) and not float(value).is_integer()
            else f"{int(value)}"
            if isinstance(value, (int, float))
            else str(value)
        )
        parts.append(
            f"{human_name(feat)} (= {v}) {direction_phrase(c)} the risk score by {abs(c):.2f} {units}"
        )
    body = "; ".join(parts)
    return (
        f"Ranked #{rank} for review in {period_label} with risk score {score:.4f}. The largest influences: {body}. "
        f"This is a prioritisation for human review, not a finding. {DISCLAIMER}"
    )


def global_caption(top: list[tuple[str, float]], units: str = "mean |SHAP| in log-odds") -> str:
    body = ", ".join(f"{human_name(f)} ({v:.3f})" for f, v in top)
    return f"Features that move the risk score most across the sampled test transactions ({units}): {body}. {DISCLAIMER}"


def feature_rationale(defs: list[FeatureDef], feature: str) -> str:
    name = "type_onehot" if feature.startswith("type_") else feature
    for d in defs:
        if d.name == name:
            return d.rationale
    return ""
