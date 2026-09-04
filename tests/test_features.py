from __future__ import annotations

from pathlib import Path

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
        features_for_set(
            registry, "pca_variant"
        )  # produced by the pca command, never a registry set


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


# ---- Milestone 4: selection and PCA fit scope ----
import yaml  # noqa: E402

from aml_triage.config import load as load_cfg  # noqa: E402
from aml_triage.data.split import make_split, write_split  # noqa: E402
from aml_triage.features.pca import run_pca  # noqa: E402
from aml_triage.features.pipeline import (  # noqa: E402
    build_feature_matrices,
    load_feature_matrix,
    read_fitscope,
)
from aml_triage.features.selection import (  # noqa: E402
    registry_name,
    run_selection,
    update_registry_selected,
)


@pytest.fixture
def m4_cfg(tmp_path, repo_root, fixture_frame):
    import shutil

    reg = tmp_path / "features.yaml"
    shutil.copy(repo_root / "configs" / "features.yaml", reg)
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "_extends": str(repo_root / "configs" / "base.yaml"),
                "paths": {
                    "processed_dir": str(tmp_path / "processed"),
                    "reports_dir": str(tmp_path / "reports"),
                    "raw_csv": str(tmp_path / "f.csv"),
                },
                "features": {"registry": str(reg)},
                "split": {"train_end_step": 40, "val_end_step": 56, "min_positives_per_split": 1},
                "review": {"review_period_steps": 24, "primary_k": 5, "k_grid": [5, 10]},
                "tuning": {"tune_sample_rows": 100000},
                "selection": {"mi_k": 6, "l1_c": 0.5, "min_size": 3},
                "pca": {"n_components": 0.95},
            }
        )
    )
    cfg = load_cfg(cfg_path)
    parts, manifest = make_split(fixture_frame, cfg)
    write_split(parts, manifest, cfg.paths.processed_dir)
    build_feature_matrices(cfg, "primary")
    build_feature_matrices(cfg, "strict_pretx")
    return cfg


def test_selection_fitted_on_train_only(m4_cfg) -> None:
    result = run_selection(m4_cfg, "primary")
    assert result["fit_scope"]["mi"]["fitted_on"] == ["train"]
    assert result["fit_scope"]["l1"]["fitted_on"] == ["train"]
    assert 0 < len(result["selected_columns"]) <= len(result["before"])
    assert set(result["selected_columns"]) <= set(result["before"])
    assert not (set(result["constant_columns"]) & set(result["selected_columns"]))


def test_selection_on_strict_set_has_no_batch_only(m4_cfg) -> None:
    result = run_selection(m4_cfg, "strict_pretx")
    batch_only = {
        d.name
        for d in load_registry(m4_cfg.features.registry)
        if d.available_at_prediction_time == "batch_only"
    }
    assert not (batch_only & {registry_name(c) for c in result["selected_columns"]})


def test_registry_selected_set_updated_preserving_comments(m4_cfg) -> None:
    result = run_selection(m4_cfg, "primary")
    path = update_registry_selected(m4_cfg.features.registry, result["selected_registry_features"])
    text = path.read_text()
    assert text.startswith("# Feature registry")  # comments preserved
    sel = {d.name for d in features_for_set(load_registry(path), "selected")}
    assert sel == set(result["selected_registry_features"])


def test_pca_fit_scope_and_variant_matrices(m4_cfg) -> None:
    result = run_pca(m4_cfg, "primary", n_neg_sample=100)
    assert result["fit_scope"]["fitted_on"] == ["train"]
    assert sorted(result["fit_scope"]["transformed_on"]) == [
        "test",
        "train",
        "train",
        "val",
    ]  # projection sample + 3 splits
    assert result["cumulative"][-1] >= 0.95 or result["n_components"] == len(result["inputs"])
    assert read_fitscope(m4_cfg.paths.processed_dir, "pca_variant")["fitted_on"] == ["train"]
    X, meta = load_feature_matrix(m4_cfg.paths.processed_dir, "pca_variant", "test")
    assert all(c.startswith(("PC", "type_")) for c in X.columns)
    assert "isFraud" in meta.columns
    assert (Path(m4_cfg.paths.reports_dir) / "pca_report.md").exists()
