# Business Deck Outline — Explainable AML Transaction-Risk Triage

Audience: compliance and financial-crime executives (non-technical). 10 slides. Every number is an
**illustrative** count on synthetic data; nothing is a real-world estimate and nothing is in currency.
Speaker notes in italics. Source artifacts named per slide so every figure is traceable.

---

## Slide 1 — Title
**Explainable AML Transaction-Risk Triage for SME and Corporate Banking**
An educational prototype that helps investigators decide what to review first.
Julius Pabular · Pillar 5 Capstone · released model `20260904T225142-0dc8f82-hgb`
> Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.

## Slide 2 — The problem we chose
- Investigators can review only a fixed number of transactions a day; most alerts are never looked at in depth.
- The question the prototype answers: *of today's transactions, which 200 deserve a human look first?*
- Built and tested on **synthetic** PaySim data because labelled real SME/corporate data is not public.
*Source: `reports/sections/01_problem.md`.*

## Slide 3 — What the tool does, and does not do
**Does:** ranks each day's transactions, returns a risk score, a review priority (high / medium / low), the three factors behind each score, the model version, and a disclaimer.
**Does not:** block or hold transactions, close or freeze accounts, rate customers, file suspicious-activity or regulatory reports, or decide that anything is fraud. A person reviews, decides, and can override.
*Source: spec non-use list; model card.*

## Slide 4 — How investigators would use it (human-in-the-loop)
1. Each morning the queue lists the top 200 transactions of the previous day with plain-language reasons.
2. The investigator works the queue, records a decision, and may override or pull in any other transaction.
3. Decisions and overrides feed monitoring and, in any real deployment, the fairness audit.
*Source: `reports/review_queue_period_0.md` (example queue), `reports/explainability.md` (reasons).*

## Slide 5 — Illustrative result: what 200 reviews a day would surface
| Way of choosing the 200 reviews | Illustrative positives surfaced per day |
|---|---|
| **This prototype** | **200** |
| Simple rule (flag, then largest amount) | 83 |
| Oldest first | 56 |
| Random | 28 |
Illustrative counts from the held-out test period (76% of each day's positives caught; every one of the 200 reviews landed on a positive). Improvement factor vs the simple rule: 2.4×.
*Source: `reports/capacity_analysis.md`.*

## Slide 6 — Why the illustrative numbers look too good
- The synthetic generator writes simulated fraud with a bookkeeping signature (account emptied, balances reconcile exactly). The model learned that signature, which is why it looks perfect here.
- On real transactions this signature would not exist. **The method transfers; the numbers do not.**
- What does carry over: the ranking-under-capacity design, the honesty checks, and the audit trail.
*Source: `reports/explainability.md`, `reports/model_comparison.md`.*

## Slide 7 — Capacity, not the model, is the constraint
- Illustrative: each test day had 240–280 simulated positives but only 200 review slots, so about 24% of positives wait unreviewed even with a perfect ranking.
- Illustrative: raising capacity to 300 catches every positive at the cost of roughly 30 reviews a day spent on normal transactions.
- Small-value and low-balance positives are the ones that wait: an operational effect of ranking under capacity, addressed in the mitigations.
*Source: `reports/capacity_analysis.md`, `reports/bias_fairness_analysis.md`.*

## Slide 8 — Risks and how they are handled
| Risk | Handling |
|---|---|
| Over-trusting a synthetic result | Every report states results cannot establish real-world effectiveness, fairness or regulatory suitability |
| Model relies on data artifacts | Documented; a variant without post-transaction fields performs equally; permutation checks in the monitoring plan |
| Fairness cannot be measured on this data | Stated plainly; only operational error slices are reported; a governance-controlled audit plan is defined for real use |
| Silent changes to the test result | The test split was scored once; any re-evaluation is recorded with a reason |
| Misuse as an automated decision | No decision outputs exist; disclaimer on every surface; human override by design |
*Source: `reports/bias_fairness_analysis.md`, `data/processed/test_access.json`.*

## Slide 9 — What a real deployment would require
- Lawfully obtained, consented data with a validated label; a governance-controlled fairness audit (owners, metrics, quarterly cadence) before go-live.
- Monitoring of drift, prevalence, Recall@K and slice error rates; capacity-aware slot reservation for small-value cases.
- Model-risk review of feature reliance; a human-in-the-loop workflow with recorded overrides.
- Strategy: treat this as a **triage design and governance template**, not a model to ship.
*Source: `reports/bias_fairness_analysis.md` (mitigations, audit plan).*

## Slide 10 — Next steps and the ask
- Pilot the ranking-under-capacity design on a governed, real dataset with the audit plan in place.
- Decide the review capacity K and the slot-reservation share with operations.
- Keep the prototype's controls: single-touch evaluation, disclaimer on every output, override records.
> Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.
