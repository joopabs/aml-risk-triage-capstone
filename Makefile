# Explainable AML Transaction-Risk Triage — reproducible commands (README documents these).
SHELL := /bin/bash
PY ?= .venv/bin/python
UV ?= uv
CONFIG ?= configs/base.yaml
# Set when the tracked test-access record is already "evaluated" (e.g. a clean clone), so the audited
# re-evaluation path is used: EVALUATE_FLAGS='--force-reevaluate --reason "clean-clone reproducibility run"'
EVALUATE_FLAGS ?=
COV_MIN ?= 80
OMP_NUM_THREADS ?= $(shell $(PY) -c "import yaml;print(yaml.safe_load(open('$(CONFIG)'))['compute']['omp_num_threads'])" 2>/dev/null || echo 4)
export OMP_NUM_THREADS
CLI := $(PY) -m aml_triage

.PHONY: help setup lint format test coverage data pipeline report slides package smoke ci check-no-data api docker-build docker-run clean-derived

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
	$(CLI) build-features --config $(CONFIG) --feature-set posttx_ablation
	$(CLI) eda --config $(CONFIG)
	$(CLI) select-features --config $(CONFIG)
	$(CLI) build-features --config $(CONFIG) --feature-set selected
	$(CLI) pca --config $(CONFIG)
	$(CLI) train --config $(CONFIG) --models dummy,logreg,balanced_rf,hgb --feature-set primary --split val
	$(CLI) train --config $(CONFIG) --models dummy,logreg,balanced_rf,hgb --feature-set strict_pretx --split val
	$(CLI) train --config $(CONFIG) --models hgb --feature-set posttx_ablation --split val
	$(CLI) train --config $(CONFIG) --models hgb --feature-set selected --split val
	$(CLI) train --config $(CONFIG) --models hgb --feature-set pca_variant --split val
	$(CLI) compare --config $(CONFIG) --split val
	$(CLI) tune --config $(CONFIG) --models logreg,balanced_rf,hgb
	$(CLI) choose-operating-point --config $(CONFIG)
	$(CLI) freeze --config $(CONFIG)
	$(CLI) evaluate --config $(CONFIG) --split test $(EVALUATE_FLAGS)
	$(CLI) select --config $(CONFIG)
	$(CLI) reproduce-check --config $(CONFIG)
	$(CLI) explain --config $(CONFIG) --model LATEST
	$(CLI) fairness-availability --config $(CONFIG)
	$(CLI) fairness --config $(CONFIG)
	$(CLI) build-report --config $(CONFIG)

report: ## Assemble and export the final report
	$(CLI) build-report --config $(CONFIG)
	scripts/export_report.sh

package: ## Copy the deliverables into submission/ (gitignored) with submission names (T101)
	scripts/package_submission.sh $(NAME)

slides: ## Export the technical deck from the notebook
	$(PY) -m nbconvert notebooks/90_technical_deck.ipynb --to slides --output-dir reports/slides --output technical_deck && mv -f reports/slides/technical_deck.slides.html reports/slides/technical_deck.html
	$(PY) -m nbconvert notebooks/90_technical_deck.ipynb --to markdown --output-dir reports/slides --output .technical_deck && $(PY) scripts/md_to_html.py reports/slides/.technical_deck.md reports/slides/.technical_deck.html abs && $(PY) scripts/html_to_pdf.py reports/slides/.technical_deck.html reports/slides/technical_deck.pdf --page-break-h2 && rm -f reports/slides/.technical_deck.md reports/slides/.technical_deck.html
	$(PY) scripts/build_business_deck.py && $(PY) scripts/md_to_html.py reports/slides/business_deck_outline.md reports/slides/.business_deck.html abs && $(PY) scripts/html_to_pdf.py reports/slides/.business_deck.html reports/slides/business_deck.pdf --page-break-h2 && rm -f reports/slides/.business_deck.html
	$(PY) scripts/check_slide_counts.py reports/slides/technical_deck.html reports/slides/business_deck.pptx --dump-text

smoke: ## CI smoke pipeline on a synthetic sample (available from task T063)
	@if [ -f scripts/make_sample.py ]; then \
		rm -rf data/processed/smoke data/processed/smoke_sample.csv models/smoke reports/smoke && \
		mkdir -p models/smoke && cp configs/features.yaml models/smoke/features.yaml && \
		$(PY) scripts/make_sample.py --config configs/smoke.yaml && $(CLI) validate-schema --config configs/smoke.yaml \
		&& $(CLI) profile --config configs/smoke.yaml && $(CLI) data-dictionary --config configs/smoke.yaml \
		&& $(MAKE) pipeline CONFIG=configs/smoke.yaml && $(CLI) queue --config configs/smoke.yaml --period 0; \
	else echo "smoke pipeline not available yet (task T063); skipping"; fi

check-no-data: ## Fail if any data file is tracked by git
	@if git ls-files | grep -E '^data/(raw|processed)/.+\.(csv|parquet)$$'; then echo "ERROR: data files are tracked"; exit 1; fi
	@if git ls-files | grep -E '(^|/)\.env$$'; then echo "ERROR: .env is tracked"; exit 1; fi
	@echo "no data or .env files tracked"

ci: lint test check-no-data smoke ## Everything CI runs

api: ## Optional Step 8: run the local scoring service
	$(PY) -m uvicorn aml_triage.api.main:app --port 8000

docker-build: ## Optional Step 8: build the API image with the released bundle
	docker build -t aml-triage-api -f deployment/Dockerfile --build-arg MODEL_VERSION=$$(cat models/LATEST) .

docker-run: ## Optional Step 8: run the API container on :8000
	docker run --rm -p 8000:8000 --name aml-triage-api aml-triage-api

clean-derived: ## Remove regenerable artifacts (keeps raw data and .gitkeep files)
	find data/processed -mindepth 1 ! -name .gitkeep ! -name test_access.json ! -name split_manifest.json -delete  # keep the tracked audit records
	rm -rf models/runs models/smoke reports/smoke
	find reports/figures -type f ! -name .gitkeep -delete
