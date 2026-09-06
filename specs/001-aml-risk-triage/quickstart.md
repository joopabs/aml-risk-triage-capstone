# Quickstart: Reviewer Validation Guide

Proves the feature works end to end from a clean clone. Commands are the same ones the README
will document; details of outputs are in [contracts/](contracts/) and
[data-model.md](data-model.md). This guide does not contain implementation code.

> Educational decision-support prototype on synthetic PaySim data. Nothing here blocks
> transactions, rates customers, files reports, or makes AML determinations.

## Prerequisites

- Python 3.11.12 (pyenv: `pyenv install 3.11.12`), `uv` (`pip install uv` or standalone)
- ~15 GB free disk, 16 GB RAM recommended
- One-time access to the Kaggle dataset page to download PaySim and read its license
- Optional: pandoc (PDF export), Docker (optional Step 8)

## 1. Environment (M1)

```bash
git clone <repo-url> && cd aml-risk-triage-capstone
make setup                      # creates .venv, syncs pinned requirements(+dev), installs package editable
source .venv/bin/activate
make lint && make test          # expected: ruff clean; starter tests pass
pre-commit run --all-files      # expected: all hooks pass, including detect-secrets
```

## 2. Data acquisition and validation (M2)

```bash
make data                       # Kaggle API if KAGGLE_* env set; else follow printed manual steps
python -m aml_triage validate-schema     # expected: exit 0, prints column/dtype summary
python -m aml_triage profile             # expected: reports/data_quality.md + .json
python -m aml_triage data-dictionary     # expected: reports/data_dictionary.md
cat data/README.md                       # expected: URL, download date, sha256, verbatim license, synthetic notice
git status --porcelain | grep -E 'data/(raw|processed)' && echo "FAIL: data tracked" || echo "OK: no data tracked"
```

Reviewer checks: `data_quality.md` reports nulls, duplicates, outliers, invalid values, class
ratio, transactions per step, sensitive-attribute pre-scan, and limitations, with no row dumps.

## 3. Split, features, EDA (M3)

```bash
# after filling split bounds and review_period_steps in configs/base.yaml from profiling:
python -m aml_triage split
python -m aml_triage build-features --feature-set primary
python -m aml_triage build-features --feature-set strict_pretx
python -m aml_triage eda
pytest tests/test_split.py tests/test_leakage.py tests/test_aggregates_causal.py -q   # expected: pass
cat data/processed/split_manifest.json   # expected: temporal strategy, increasing step ranges, positives per split ≥ minimum
```

## 4. Selection and PCA (M4)

```bash
python -m aml_triage select-features && python -m aml_triage pca
# expected: reports/feature_selection.md with before/after lists; reports/pca_report.md stating PCA role
```

## 5. Validation comparison (M5)

```bash
python -m aml_triage train --models dummy,logreg,balanced_rf,hgb --split val
python -m aml_triage compare --split val
python -m aml_triage train --models hgb --split test    # expected: exit 3 "test split locked; run freeze first"
```

## 6. Tuning, operating point, single-touch test, selection (M6)

```bash
python -m aml_triage tune --models logreg,balanced_rf,hgb
python -m aml_triage choose-operating-point       # writes configs/operating_point.yaml
python -m aml_triage freeze
python -m aml_triage evaluate --split test        # expected: metrics with bootstrap CIs for all candidates
python -m aml_triage evaluate --split test        # expected: exit 3 "already evaluated for this config hash"
python -m aml_triage select                       # expected: reports/selection_matrix.md, models/<version>/, models/LATEST
python -m aml_triage reproduce-check              # expected: identical metrics, or a recorded tolerance
```

Reviewer checks: selected model's Recall@K > random and dummy at the same K (SC-001);
rule-baseline comparison present (SC-002); accuracy, if shown, sits next to prevalence.

## 7. Explainability and fairness (M7)

```bash
python -m aml_triage explain --model LATEST
python -m aml_triage fairness-availability
python -m aml_triage fairness
pytest tests/test_vocabulary.py -q
grep -n "Operational Error-Slice Analysis" reports/bias_fairness_analysis.md   # expected: heading present
grep -in "demographic fairness metrics cannot be computed" reports/bias_fairness_analysis.md  # expected if availability=false
```

## 8. Report and decks (M8)

```bash
python -m aml_triage build-report && scripts/export_report.sh
make slides                                       # nbconvert technical deck; business deck exported manually to reports/slides/
python scripts/check_slide_counts.py reports/slides/technical_deck.html reports/slides/business_deck.pptx   # expected: both within 8–12
```

## 9. Full reproducibility run (SC-003)

```bash
# The split manifest and test-access record are tracked, so the replay is an audited re-evaluation:
make clean-derived && make pipeline EVALUATE_FLAGS='--force-reevaluate --reason "reproducibility run"' && make report
git diff --stat reports/*.md models/*/metrics.json   # expected: no metric differences (or within README tolerance)
# expected: data/processed/test_access.json gains one `reevaluations` entry with that reason; split_manifest.json unchanged
```

## 10. Optional Step 8 demo

```bash
uv pip sync requirements.txt requirements-api.txt
make api &                                        # uvicorn on :8000
curl -s localhost:8000/health
curl -s -X POST localhost:8000/score -H 'content-type: application/json' \
  -d @specs/001-aml-risk-triage/contracts/examples/score_request.json
# expected: risk_score, review_priority, model_version, disclaimer; no allow/block/decision field
pytest tests/api -q
```

## Pass criteria summary

| Check | Expected |
|-------|----------|
| `make lint test` | clean, all tests pass |
| Data tracked in git | none |
| Leakage tests | pass |
| Test split access before freeze | refused (exit 3) |
| Second test evaluation without reason | refused (exit 3) |
| Selected model vs random/dummy Recall@K | higher |
| Fairness report | availability record + correct branch + literal slice label |
| Decks | 8–12 slides each |
| Disclaimer | present on every report, queue, response, and deck |
