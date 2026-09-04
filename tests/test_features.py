from __future__ import annotations

import numpy as np
import pytest

from aml_triage.features import transaction as tx
from aml_triage.features.base import (
    RegistryError,
    compute_stateless,
    features_for_set,
    load_registry,
    validate_registry,
)


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_registry_loads_and_every_feature_has_rationale(registry) -> None:
    assert len(registry) >= 18
    assert all(d.rationale.strip() and d.dictionary_entry for d in registry)
    assert len({d.name for d in registry}) == len(registry)


def test_strict_pretx_excludes_batch_only(registry) -> None:
    strict = features_for_set(registry, "strict_pretx")
    assert strict and all(d.available_at_prediction_time == "realtime" for d in strict)
    primary = {d.name for d in features_for_set(registry, "primary")}
    assert {d.name for d in strict} < primary


def test_posttx_ablation_is_type_plus_batch_only(registry) -> None:
    abl = features_for_set(registry, "posttx_ablation")
    assert {d.available_at_prediction_time for d in abl if d.kind != "categorical"} == {
        "batch_only"
    }


def test_identifiers_never_direct_features(registry) -> None:
    for d in registry:
        if d.kind != "aggregate" and d.name != "dest_is_merchant":
            assert not ({"nameOrig", "nameDest"} & set(d.source_columns)), d.name


def test_registry_rejects_batch_only_in_strict(registry) -> None:
    bad = [d for d in registry]
    victim = next(d for d in bad if d.available_at_prediction_time == "batch_only")
    victim.sets = [*victim.sets, "strict_pretx"]
    with pytest.raises(RegistryError, match="strict_pretx"):
        validate_registry(bad)


def test_unfilled_sets_raise(registry) -> None:
    with pytest.raises(RegistryError, match="empty"):
        features_for_set(registry, "selected")


def test_stateless_transforms_shapes_and_guards(fixture_frame, registry) -> None:
    defs = features_for_set(registry, "primary")
    out = compute_stateless(fixture_frame, defs)
    expected = {
        d.name for d in defs if not d.is_aggregate and not d.is_fitted and d.kind != "categorical"
    }
    assert set(out.columns) == expected
    assert len(out) == len(fixture_frame)
    assert (out["log_amount"] >= 0).all()
    assert np.isfinite(out["amount_to_orig_balance_ratio"]).all()
    assert set(out["step_hour_of_day"].unique()) <= set(range(24))
    assert set(out["dest_is_merchant"].unique()) <= {0, 1}
    assert out["dest_is_merchant"].sum() == fixture_frame["nameDest"].str.startswith("M").sum()


def test_direction_aware_inconsistency_flag(fixture_frame) -> None:
    df = fixture_frame.copy()
    ci = [i for i in df.index[df["type"] == "CASH_IN"] if i != 0][
        :3
    ]  # row 0 is the planted inconsistent row
    df.loc[ci, "newbalanceOrig"] = df.loc[ci, "oldbalanceOrg"] + df.loc[ci, "amount"]
    flag = tx.orig_balance_inconsistent_flag(df)
    assert flag.loc[ci].sum() == 0
    assert flag.loc[0] == 1  # the planted inconsistent row


def test_zero_amount_flag(fixture_frame) -> None:
    df = fixture_frame.copy()
    df.loc[1, "amount"] = 0.0
    assert tx.zero_amount_flag(df).sum() == 1


def test_bucketizer_edges_fitted_on_train_only(fixture_frame) -> None:
    train = fixture_frame["amount"].to_numpy()[:400].reshape(-1, 1)
    test = fixture_frame["amount"].to_numpy()[400:].reshape(-1, 1) * 1000  # shifted distribution
    b = tx.AmountBucketizer(n_bins=10).fit(train)
    edges = b.edges_.copy()
    out = b.transform(test)
    assert np.array_equal(b.edges_, edges)  # transform never refits
    assert out.min() >= 0 and out.max() <= 10
    assert list(b.get_feature_names_out()) == ["amount_bucket"]
