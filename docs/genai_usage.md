# Generative AI usage record (optional Step 9)

This project was built with substantial generative-AI assistance, and this document records how,
honestly and specifically. Every factual statement in the reports, decks, and README was produced
from pipeline outputs (JSON metrics, generated tables, saved figures) and checked by tests; the AI
drafted prose, the learner reviewed it, and no number was typed by hand.

**Tool and model for all uses below:** Claude Code (Anthropic's command-line agent) running the model
Claude Fable 5.1 (`claude-fable-5-1`), driven through the Spec Kit workflow (`/speckit-*` commands)
by the learner, Julius Pabular, between 2026-09-04 and 2026-09-06.

## Use 1 — Governance and specification (constitution, spec, plan, tasks)

- **Purpose:** turn the assignment PDF and the learner's project decisions into a constitution, a
  feature specification, a technical plan, a data model, CLI/API contracts, and a 101-task list.
- **Representative prompt (learner):** "Create a durable constitution for this repository … The
  constitution must enforce: clear business framing … leakage-safe temporal or stratified splitting
  … a human-in-the-loop review model; no automatic blocking, account closure, customer risk rating,
  regulatory reporting, or real AML determination." (prompts are abridged and paraphrased)
- **Representative output:** `.specify/memory/constitution.md` (11 principles, 12 quality gates),
  `specs/001-aml-risk-triage/{spec,plan,research,data-model,tasks}.md`.
- **Human review performed:** the learner resolved every ambiguity the analysis pass raised
  (bonus points inside the 100, top rubric band only, Step 8 local deployment required if attempted),
  chose `primary` as the headline feature set, and approved each remediation edit before it was applied.
- **Limitations / corrections:** two `/speckit-analyze` passes found 21 inconsistencies in the
  AI-drafted artifacts (a missing `eda/` directory, undefined priority levels, a dummy-baseline
  semantics gap, terminology drift); all were corrected before implementation.

## Use 2 — Code implementation (Milestones 1–9)

- **Purpose:** implement the pipeline, tests, CI, reports, decks, and the optional API from the task list.
- **Representative prompt (learner):** "/speckit-implement Milestone 3" (and each later milestone);
  "keep primary as the headline set. proceed with the next milestone".
- **Representative output:** `src/aml_triage/` (config, CLI with 22 commands, data, features,
  models, evaluation, explain, fairness, reporting, api), `tests/` (126 tests), `.github/workflows/ci.yml`.
- **Human review performed:** the learner ran and merged every pull request, confirmed the Kaggle
  license on the dataset page, supplied the Kaggle token, decided the branch and merge policy, and
  reviewed each milestone's completion report. Automated review: ruff, pre-commit, detect-secrets,
  the leakage and test-access guard tests, the vocabulary scan, and the CI smoke pipeline.
- **Limitations / corrections (all real, all fixed in commits on the branch):**
  - The first operating point collapsed to a threshold of 1.0 because isotonic calibration mapped a
    perfectly separable validation split to 0/1; the AI caught this before any test access and
    changed the rule to threshold on raw scores (audited re-freeze in `data/processed/test_access.json`).
  - The CI smoke pipeline's `tune` overwrote the real 1,000,000-row tuned parameters and the AI
    committed that state; it was detected on the next run, restored from the prior commit, verified
    with `reproduce-check`, and prevented by isolating tuned paths per configuration.
  - A notebook was committed twice with a syntax error before being verified; a compile-all-notebooks
    test was added afterwards.
  - The AI initially committed a milestone with one failing test and corrected it in a follow-up.
  - Long training jobs were killed twice by the operating system for memory; the evaluation was
    restructured to run each refit in a fresh subprocess.

## Use 3 — Narrative sections written from generated results

- **Purpose:** draft the human-readable narratives (data-quality findings, EDA observations,
  selection reasoning, capacity analysis, explainability consistency notes, fairness limitations and
  mitigations, report sections, slide outlines).
- **Representative prompt (task list rule):** "any task whose output is prose about data or model
  results … is sequenced strictly AFTER the task that produces the numbers, and its acceptance
  criteria require citing the generated artifact."
- **Representative output:** `reports/*_narrative.md`, `reports/sections/*.md`,
  `reports/slides/business_deck_outline.md`.
- **Human review performed:** every narrative was written after the AI had read the generated tables
  and viewed the figures; numbers in prose are copied from `reports/*.json` and the technical deck
  pulls them programmatically. The learner reviewed the completion reports and the delivered PDFs.
- **Limitations / corrections:** the vocabulary scan (`tests/test_vocabulary.py`) rejected
  determination language twice (a schema description and a deck outline lacking the verbatim
  disclaimer); both were reworded.

## Use 4 — Commit messages, pull-request descriptions, and this document

- **Purpose:** conventional-prefix commit messages, PR bodies, and documentation.
- **Representative prompt (learner):** "let's create the PR"; "explain the us2 items".
- **Representative output:** commit history on `main`; PR #1–#4 descriptions.
- **Human review performed:** the learner pasted, edited where desired, and merged each PR.
- **Limitations / corrections:** none beyond the items above.

## What generative AI did not do

- It did not download the dataset without the learner's token, did not confirm the license (the
  learner read the Kaggle page), did not choose the headline feature set, and did not merge to `main`.
- It did not invent any dataset statistic, model score, or fairness result: every figure traces to a
  generated artifact, and the test split was scored exactly once.

## Demo video

No screen-recorded video was produced. `deployment/demo/demo.gif` is a rendered terminal transcript
of real API responses (see `deployment/DEPLOYMENT.md`).
