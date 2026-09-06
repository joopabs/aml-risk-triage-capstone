# Rubric Self-Assessment (Pillar 5 Capstone)

Assessed against the **Outstanding/Exemplary** descriptors only (project decision; see
`CAPSTONE_BRIEF.md` §5). Each descriptor lists the evidence that a grader can open. Gaps are stated,
not hidden. Bonus points sit inside the 100-point total.

## 1. Problem Understanding & Framing (10 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| Problem clearly framed with strong business context and data science perspective | [`reports/sections/01_problem.md`](sections/01_problem.md); spec `specs/001-aml-risk-triage/spec.md` Business Context | met |
| Task type correctly identified and justified | binary classification on `isFraud`, score used for ranking; §1 task table | met |
| Success metrics (technical + business KPIs) relevant, measurable, well-explained | PR-AUC primary, Recall@K operational, illustrative KPI vs comparators; SC-001/SC-002 evaluated with numbers in §1 | met |

## 2. Data Collection & Understanding (10 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| High-quality dataset chosen and justified (source cited) | PaySim, Kaggle `ealaxi/paysim1`, CC BY-SA 4.0, SHA-256 recorded: [`data/README.md`](../data/README.md), `configs/data_source.yaml` | met |
| Comprehensive overview: feature types, missing values, outliers, distributions | [`reports/data_quality.md`](data_quality.md) (nulls, duplicates, IQR outliers, invalid values, imbalance by type and step) | met |
| Clear, complete data dictionary (variables, types, ranges/units) | [`reports/data_dictionary.md`](data_dictionary.md) — raw and engineered variables with prediction-time availability | met |

## 3. Data Preprocessing, EDA & Feature Engineering (10 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| All preprocessing documented with reproducible code | `src/aml_triage/data/`, `src/aml_triage/features/`; `make pipeline`; fit-scope records | met |
| Clear handling of nulls, outliers, duplicates | DQ-01..DQ-13 decisions in `data_quality.md` (0 nulls; 543 near-duplicates kept; outliers kept + log transform) | met |
| Insightful applied EDA with visuals, distributions, correlations | [`reports/eda_summary.md`](eda_summary.md), 11 figures with reviewed observations | met |
| Feature engineering shows domain knowledge and creativity | 21-feature registry with rationale (account-emptying ratio, causal aggregates, bookkeeping flags labelled as artifacts) | met |
| ≥1 feature selection + dimensionality reduction method used and justified | MI filter + L1 embedded ([`feature_selection.md`](feature_selection.md)); PCA diagnostic ([`pca_report.md`](pca_report.md)) | met |

## 4. Model Implementation & Comparison (20 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| Multiple models implemented and tuned appropriately | dummy, class-weighted logistic regression, balanced random forest, histogram gradient boosting; RandomizedSearchCV (`configs/models/*.tuned.yaml`) | met |
| Evaluation metrics correctly applied and compared across models | [`reports/model_comparison.md`](model_comparison.md): PR-AUC, ROC-AUC, Recall@K grid, Precision@K, Brier, ECE, confusion; comparators; single-touch test with bootstrap CIs | met |
| Reproducibility ensured (saved models/configs) | bundle `models/20260904T225142-0dc8f82-hgb/` (sha256, config snapshot, metrics, model card); `reports/reproducibility.json` (exact) | met |
| Clear reasoning for model choice based on results | [`reports/selection_matrix.md`](selection_matrix.md): deterministic key, validation-only verdict, test numbers beside | met |

## 5. Critical Thinking, Ethical AI & Bias Auditing (20 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| Excellent use of explainability tools (SHAP/LIME/PDP/ICE) | [`reports/explainability.md`](explainability.md): SHAP global + 3 local, PDP/ICE with validity gate, permutation importance | met |
| Thorough discussion of data/model limitations (imbalance, leakage, overfitting) | [`reports/sections/07_limitations.md`](sections/07_limitations.md); Bias & Fairness Limitations | met |
| Bias audit performed across sensitive groups with fairness metrics | **Gap, acknowledged:** PaySim has no sensitive attributes (availability record from actual columns). Demographic metrics are implemented and unit-tested; the report states non-measurability and provides an operational error-slice analysis labelled as such. [`reports/bias_fairness_analysis.md`](bias_fairness_analysis.md) | partially met by design |
| Proposes clear, feasible mitigation strategies | Mitigations with mechanism / owner / trigger; governance-controlled audit plan | met |

## 6. Final Presentation & Communication (10 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| Two high-quality, well-structured presentations | `reports/slides/technical_deck.html` (11 slides), `reports/slides/business_deck.pptx` (10 slides) | met |
| Technical deck: clear methodology, visuals, metrics | numbers pulled from `metrics.json` at build time; figures embedded | met |
| Business deck: ROI, risks, strategy for a non-technical audience | illustrative KPI table, risks table, deployment requirements, next steps; every number labelled illustrative | met |
| Visually professional and concise (8–12 slides) | `scripts/check_slide_counts.py` enforces 8–12; PPTX built from the outline (open in PowerPoint for final polish/PDF export) | met |

## 7. GitHub Profile & Upload (15 pts)

| Descriptor | Evidence | Status |
|---|---|---|
| Public repo structured like an open-source project (src/, notebooks/, data/, models/) | https://github.com/joopabs/aml-risk-triage-capstone | met |
| README, requirements.txt, final report, reproducible code | [`README.md`](../README.md), pinned `requirements.txt`, [`reports/final_report.md`](final_report.md) / `.pdf`, `make pipeline` | met |
| Clean, professional commit history | conventional prefixes, PR-based merges to `main`, CI green | met |

## Bonus: Creative and well-presented submission (5 pts, inside the 100)

| Descriptor | Evidence | Status |
|---|---|---|
| Exceptional creativity, originality, clear presentation; goes beyond expectations | Governance mechanics: single-touch test with audited access record, fit-scope recorder, vocabulary scan for determination language, validation-frozen operating point, narrative files that survive regeneration. Optional Step 8 attempted: FastAPI scoring service with contract tests, Docker image, deployment guide, demo ([`deployment/DEPLOYMENT.md`](../deployment/DEPLOYMENT.md), `deployment/demo/demo.gif`, [`docs/mlops_plan.md`](../docs/mlops_plan.md)). Optional Step 9 attempted: honest GenAI usage record incl. corrections ([`docs/genai_usage.md`](../docs/genai_usage.md)). | met |

## Summary

All seven criteria have evidence at the exemplary level except the protected-group bias audit, which
this dataset cannot support and which the report addresses honestly with an operational error-slice
analysis and an audit plan for real data. Optional Steps 8 and 9 were attempted and documented.
Test result of the released model for reference: PR-AUC 1.0000, Recall@200 0.7568 on synthetic data.

---

_Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability._
