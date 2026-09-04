# Capstone Brief: Pillar 5 Capstone Project

Source: `references/Pillar5_Capstone_Project.pdf` (5 pages). This brief extracts the assignment requirements as written. Points where the PDF was ambiguous have been resolved per the learner's clarifications, recorded on 2026-09-04, and are marked "Clarified".

## 1. Assignment objective and learning outcomes

**Objective (as stated):** To demonstrate the end-to-end application of the machine learning lifecycle, including problem framing, data preprocessing, modelling, evaluation, and result communication, on a real-world, industry-relevant dataset of choice.

**Learning outcomes addressed:**

- Develop a robust foundational understanding of artificial intelligence (AI) and machine learning (ML) concepts and technologies.
- Equip learners with the knowledge and skills to identify and implement AI solutions across various sectors effectively.
- Develop proficiency in AI/ML tools and frameworks.
- Develop a holistic understanding of AI concepts and techniques, enabling learners to effectively address complex real-world problems by designing, implementing, and evaluating AI and ML models.
- Develop hands-on skills in modelling, training, and deploying these models in real-world applications.

**Assignment instructions:**

- You must attempt all the given tasks.
- The assignment carries a maximum of 100 points.
- Ensure clarity, depth, and relevance in your answers to maximize your score.

## 2. Eligible project domains

Choose one. Learners may choose from the following or propose a custom domain (with approval):

| Domain | Example task |
|---|---|
| Healthcare | Predict patient readmission or disease likelihood |
| Finance | Detect fraudulent transactions |
| eCommerce | Recommend products to users |
| Education | Predict student dropout risk |
| Cybersecurity | Detect anomalies in network traffic |
| Clustering option (unsupervised) | Group customers, behaviors, or products based on similarity (K-Means, DBSCAN, Hierarchical) |

## 3. Required ML lifecycle steps

Steps 1 through 7 are required. Steps 8 and 9 are optional (see sections 6 and 7); implementing them counts toward the 5 bonus points.

### Step 1: Problem Understanding & Framing

- Frame the business and data science problem clearly.
- Define whether it is a classification, regression, recommendation, anomaly detection, or clustering task.
- Specify success metrics (e.g., Accuracy, AUC, RMSE, Silhouette Score) and business KPIs (e.g., cost savings, uplift).
- Capstone linkage: Module 1 output maps to Capstone Steps 1–3.
- **Deliverable:** Clear problem statement + task type + target metric.

### Step 2: Data Collection & Understanding

- Use public datasets (Kaggle, UCI, APIs, etc.) or approved custom data.
- Summarize feature types, missing values, outliers, etc.
- Provide a data dictionary (variables, types, units, allowed values).
- **Deliverable:** Dataset overview + data dictionary.

### Step 3: Data Preprocessing, Applied EDA & Feature Engineering

- Clean data: handle nulls, duplicates, and outliers.
- Engineer features: scaling, encoding, binning, and domain-derived features.
- Applied EDA: distributions, relationships, clustering tendency (if unsupervised).
- Feature importance and explainability: SHAP, LIME, or model-based importances.
- Feature selection: at least one approach (filter, wrapper, or embedded).
- Dimensionality reduction: PCA (and t-SNE/UMAP for visualization if needed).
- **Deliverable:** "EDA + Feature Engineering Report" with reproducible code and justifications.

### Step 4: Model Implementation

- Experiment with appropriate models:
  - Supervised: Logistic Regression, Decision Trees, Random Forest, XGBoost, SVM, etc.
  - Unsupervised: K-Means, DBSCAN, Hierarchical (Elbow, Silhouette).
  - Recommendation: collaborative or content-based.
  - Deep Learning: RNNs, CNNs, LSTMs, Transformers (if appropriate).
- Evaluation: compare with relevant metrics.
- Reproducibility: save configs and artifacts (models).
- **Deliverables:** Trained models, metrics, and comparison between models.

### Step 5: Critical Thinking, Ethical AI & Bias Auditing

- Explain model decisions (SHAP, LIME, PDP, ICE).
- Address limitations (imbalance, leakage, overfitting).
- Bias detection and fairness audits:
  - Check outputs across sensitive groups (gender, race, age, socioeconomic status).
  - Use fairness metrics (demographic parity, equalized odds, disparate impact).
  - Propose mitigations (reweighting, thresholds, augmentation, post-processing).
- **Deliverable:** "Bias & Fairness Analysis" section in the final report.

### Step 6: Final Presentation & Communication

- Two deliverables for mixed audiences:
  1. Technical presentation (Jupyter slides / LaTeX Beamer) for peers.
  2. Business-facing presentation (PowerPoint / Canva) for executives (ROI, risks, strategy).
- 8–12 slides per deck recommended.
- **Deliverables:** Two slide decks (technical + business).

### Step 7: GitHub Profile & Upload

- Create a public GitHub repo structured like an open-source project.
- Include `src/` for scripts, plus `notebooks/`, `data/`, and `models/` directories.
- **Deliverables:** GitHub repo link + final report + reproducible code.

## 4. Required deliverables

Consolidated from Steps 1–7 and the rubric:

| Step | Deliverable |
|---|---|
| 1 | Clear problem statement, task type, and target metric |
| 2 | Dataset overview and data dictionary (variables, types, units/ranges, allowed values) |
| 3 | "EDA + Feature Engineering Report" with reproducible code and justifications |
| 4 | Trained models, metrics, and comparison between models; saved configs and model artifacts |
| 5 | "Bias & Fairness Analysis" section in the final report |
| 6 | Two slide decks: technical (peers) and business-facing (executives); 8–12 slides each recommended |
| 7 | Public GitHub repo link, final report, and reproducible code |

The rubric for Step 7 additionally lists: README, `requirements.txt`, final report, reproducible code, and a clean, professional commit history.

## 5. Evaluation rubric and point allocation

Total points stated in the rubric: **100**. Maximum stated in the assignment instructions: **100**. The 5 bonus points are part of this total (Clarified).

| Criterion | Points | "Outstanding/Exemplary" band |
|---|---|---|
| 1: Problem Understanding & Framing | 10 | 10 to >5.0 pts |
| 2: Data Collection & Understanding | 10 | 10 to >5.0 pts |
| 3: Data Preprocessing, EDA & Feature Engineering | 10 | 10 to >5.0 pts |
| 4: Model Implementation & Comparison | 20 | 20 to >10.0 pts |
| 5: Critical Thinking, Ethical AI & Bias Auditing | 20 | 20 to >10.0 pts |
| 6: Final Presentation & Communication | 10 | 10 to >5.0 pts |
| 7: GitHub Profile & Upload | 15 | 15 to >10.0 pts |
| Bonus: Creative and well-presented submission | 5 | 5 to >2.5 pts |

**Note on totals (Clarified):** Criteria 1–7 sum to 95 points. The 5 bonus points are counted inside the 100-point total, not added on top of it. Reaching 100 therefore requires earning the bonus.

**Note on rating bands (Clarified):** This project targets the "Outstanding/Exemplary" band on every criterion. Lower rating bands are intentionally excluded from this brief; the descriptors below are the target standard.

### Rubric descriptors ("Outstanding/Exemplary")

**1: Problem Understanding & Framing (10 pts)**
- Problem clearly framed with strong business context and data science perspective.
- Task type (classification/regression/etc.) correctly identified and justified.
- Success metrics (technical + business KPIs) are relevant, measurable, and well-explained.

**2: Data Collection & Understanding (10 pts)**
- High-quality dataset chosen and justified (source cited).
- Comprehensive dataset overview: feature types, missing values, outliers, distributions.
- Clear, complete data dictionary (variables, types, ranges/units).

**3: Data Preprocessing, EDA & Feature Engineering (10 pts)**
- All preprocessing steps documented with reproducible code.
- Clear handling of nulls, outliers, and duplicates.
- Insightful applied EDA with visuals, distributions, and correlations.
- Feature engineering shows domain knowledge and creativity.
- At least one feature selection + dimensionality reduction method used and justified.

**4: Model Implementation & Comparison (20 pts)**
- Multiple models implemented and tuned appropriately.
- Evaluation metrics correctly applied and compared across models.
- Reproducibility ensured (saved models/configs).
- Clear reasoning for model choice based on results.

**5: Critical Thinking, Ethical AI & Bias Auditing (20 pts)**
- Excellent use of explainability tools (SHAP/LIME/PDP/ICE).
- Thorough discussion of data/model limitations (imbalance, leakage, overfitting).
- Bias audit performed across sensitive groups with fairness metrics.
- Proposes clear, feasible mitigation strategies.

**6: Final Presentation & Communication (10 pts)**
- Two high-quality, well-structured presentations (technical + business).
- Technical deck: clear methodology, visuals, metrics.
- Business deck: ROI, risks, strategy clearly communicated for a non-technical audience.
- Visually professional and concise (8–12 slides per deck).

**7: GitHub Profile & Upload (15 pts)**
- Public GitHub repo structured like an open-source project (`src/`, `notebooks/`, `data/`, `models/`).
- Includes README, `requirements.txt`, final report, reproducible code.
- Clean, professional commit history.

**Bonus: Creative and well-presented submission (5 pts)**
- Demonstrates exceptional creativity, originality, and clear presentation.
- The submission goes beyond expectations in terms of design, clarity, or innovation.

## 6. Optional deployment and MLOps requirements

**(Optional) Step 8: Deployment & MLOps.** Complete this step if you have a good understanding of model deployment and MLOps practices.

- Local deployment (required): deploy the best model via Flask, FastAPI, or Dash.
- Optional cloud: AWS SageMaker, GCP Vertex AI, or Azure ML.
- MLOps practices:
  - Reproducible environments (`requirements.txt`, Docker).
  - Config-driven runs and experiment tracking (MLflow, W&B, etc.).
  - CI checks (lint, unit tests), basic monitoring plan.
  - Versioning and rollback plan.
- Provide a demo (GIF/screencast).
- **Deliverables:** Running app + deployment guide + demo media.

**Note (Clarified):** Step 8 as a whole is optional. If Step 8 is included, local deployment (Flask, FastAPI, or Dash) becomes required; cloud deployment remains optional. No rubric criterion is dedicated to Step 8. Implementing it counts toward the bonus criterion "Creative and well-presented submission" (see section 7).

## 7. Optional Generative AI bonus requirements

**(Optional) Step 9: Use of Generative AI.** You may optionally use Generative AI tools to:

- Use LLMs to auto-generate EDA summaries or data dictionaries.
- Build GenAI-enhanced applications (e.g., LLM-backed recommenders, chatbots).

**Deliverable:**

- Document how Generative AI was used in the project.
- Include code and examples in the GitHub repo or presentation.
- Demo video.

**Bonus points (Clarified):** Up to 5 points, counted inside the 100-point total, are awarded for a creative and well-presented submission. The rubric's bonus criterion is "Creative and well-presented submission" (5 to >2.5 pts for Outstanding/Exemplary). Opting to implement Step 8 (Deployment & MLOps) and/or Step 9 (Generative AI) counts toward this bonus. Neither step is strictly required to earn it, but they are the stated avenues for going beyond expectations.

## 8. Submission checklist

Submission instructions from the PDF:

- [ ] Go through the instructions and evaluation rubric to understand what is expected.
- [ ] Collate all textual responses in a file (recommended). Record responses in an approved format: `.pdf`, `.doc`, `.pptx`, or `.ppt`.
- [ ] Submit the coding files.
- [ ] Rename the files as `Your_Name_Assignment name`.
- [ ] Select the **Start Assignment** button at the top of the assignment page.
- [ ] Upload the file containing your responses.
- [ ] Select the **Submit Assignment** button.

Required content to include (from Steps 1–7 and rubric):

- [ ] Problem statement, task type, and target metric (Step 1)
- [ ] Dataset overview and data dictionary, with source cited (Step 2)
- [ ] EDA + Feature Engineering Report with reproducible code, including at least one feature selection method and one dimensionality reduction method (Step 3)
- [ ] Trained models, saved configs/artifacts, metrics, and model comparison (Step 4)
- [ ] Bias & Fairness Analysis section in the final report, with explainability, limitations, fairness metrics, and mitigations (Step 5)
- [ ] Technical slide deck, 8–12 slides recommended (Step 6)
- [ ] Business-facing slide deck, 8–12 slides recommended (Step 6)
- [ ] Public GitHub repo with `src/`, `notebooks/`, `data/`, `models/`, README, `requirements.txt`, final report, reproducible code, and clean commit history (Step 7)
- [ ] Final report (Step 7)

Optional content (counts toward the 5 bonus points):

- [ ] Running app, deployment guide, and demo media (Step 8). If Step 8 is attempted, local deployment via Flask, FastAPI, or Dash is required.
- [ ] GenAI usage documentation, code/examples, and demo video (Step 9)
