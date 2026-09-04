# Explainable AML Transaction-Risk Triage — reproducible commands (README documents these).
SHELL := /bin/bash
PY ?= .venv/bin/python
UV ?= uv
CONFIG ?= configs/base.yaml
COV_MIN ?= 80
OMP_NUM_THREADS ?= $(shell $(PY) -c "import yaml;print(yaml.safe_load(open('$(CONFIG)'))['compute']['omp_num_threads'])" 2>/dev/null || echo 4)
export OMP_NUM_THREADS
CLI := $(PY) -m aml_triage

.PHONY: help setup lint format test coverage data pipeline report slides smoke ci check-no-data api clean-derived

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n",$$1,$$2}'

setup: ## Create .venv, sync pinned deps, install package editable, install pre-commit hooks
	python3.11 -m venv .venv
	$(UV) pip sync --python $(PY) requirements.txt requirements-dev.txt
	$(UV) pip install --python $(PY) --no-deps -e .
	$(PY) -m pre_commit install

lint: ## ruff check + format check
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format: ## ruff format + autofix
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

test: ## Run the test suite
	$(PY) -m pytest -q

coverage: ## Test suite with coverage gate (COV_MIN, enforced from task T066)
	$(PY) -m pytest -q --cov=aml_triage --cov-report=term-missing --cov-fail-under=$(COV_MIN)

data: ## Fetch the dataset (Kaggle API if credentials present, else manual steps) and verify checksum
	scripts/fetch_data.sh

pipeline: ## Full CLI sequence (contracts/cli-contract.md)
	$(CLI) split --config $(CONFIG)
	$(CLI) build-features --config $(CONFIG) --feature-set primary
	$(CLI) build-features --config $(CONFIG) --feature-set strict_pretx
	$(CLI) eda --config $(CONFIG)
	$(CLI) select-features --config $(CONFIG)
	$(CLI) pca --config $(CONFIG)
	$(CLI) train --config $(CONFIG) --models dummy,logreg,balanced_rf,hgb --split val
	$(CLI) compare --config $(CONFIG) --split val
	$(CLI) tune --config $(CONFIG) --models logreg,balanced_rf,hgb
	$(CLI) choose-operating-point --config $(CONFIG)
	$(CLI) freeze --config $(CONFIG)
	$(CLI) evaluate --config $(CONFIG) --split test
	$(CLI) select --config $(CONFIG)
	$(CLI) reproduce-check --config $(CONFIG)
	$(CLI) explain --config $(CONFIG) --model LATEST
	$(CLI) fairness-availability --config $(CONFIG)
	$(CLI) fairness --config $(CONFIG)
	$(CLI) build-report --config $(CONFIG)

report: ## Assemble and export the final report
	$(CLI) build-report --config $(CONFIG)
	scripts/export_report.sh

slides: ## Export the technical deck from the notebook
	$(PY) -m jupyter nbconvert notebooks/90_technical_deck.ipynb --to slides --output-dir reports/slides --output technical_deck

smoke: ## CI smoke pipeline on a synthetic sample (available from task T063)
	@if [ -f scripts/make_sample.py ]; then \
		$(PY) scripts/make_sample.py --config configs/smoke.yaml && $(MAKE) pipeline CONFIG=configs/smoke.yaml; \
	else echo "smoke pipeline not available yet (task T063); skipping"; fi

check-no-data: ## Fail if any data file is tracked by git
	@if git ls-files | grep -E '^data/(raw|processed)/.+\.(csv|parquet)$$'; then echo "ERROR: data files are tracked"; exit 1; fi
	@if git ls-files | grep -E '(^|/)\.env$$'; then echo "ERROR: .env is tracked"; exit 1; fi
	@echo "no data or .env files tracked"

ci: lint test check-no-data smoke ## Everything CI runs

api: ## Optional Step 8: run the local scoring service
	$(PY) -m uvicorn aml_triage.api.main:app --port 8000

clean-derived: ## Remove regenerable artifacts (keeps raw data and .gitkeep files)
	find data/processed -mindepth 1 ! -name .gitkeep -delete
	rm -rf models/runs models/smoke reports/smoke
	find reports/figures -type f ! -name .gitkeep -delete
