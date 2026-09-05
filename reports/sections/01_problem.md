# Problem Statement

## Business context

Banks serving small-and-medium enterprise (SME) and corporate clients monitor large volumes of
payment transactions for possible money-laundering or fraud indicators. Investigator capacity is
fixed and far smaller than transaction volume, so most alerts are never reviewed in depth and many
reviewed alerts are false positives. This capstone builds an **educational decision-support
prototype** that assigns each transaction a risk score and ranks transactions so that a limited
number of daily investigator reviews is spent on the transactions most worth a human look.

The prototype is trained and evaluated on **PaySim**, a public synthetic mobile-money dataset with a
simulated fraud label (Kaggle `ealaxi/paysim1`, CC BY-SA 4.0). PaySim stands in because real
SME/corporate transaction data with labels is not publicly available. Every result is therefore about
simulated fraud in synthetic data and is described as such throughout.

## Intended decision, use, and non-use

**Decision supported:** which transactions, out of all transactions in a review period, should an
investigator look at first, given a fixed capacity of K reviews? The system outputs a ranked list. A
human decides what, if anything, to do with each reviewed transaction.

**Human review workflow (FR-083).** Each simulated day the system produces a queue of the K highest
ranked transactions with a risk score, a review priority (high / medium / low), the three factors that
moved the score most, the model version, and the disclaimer. An investigator works the queue, records
a decision for each item, and may override the ranking or pull any transaction into review. Nothing
happens to a transaction or an account unless a person acts. Override and decision records feed the
monitoring plan and, in any real deployment, the fairness audit.

**Explicit non-use.** The system does not and must not: automatically block, hold or reverse
transactions; close, freeze or restrict accounts; assign a customer- or entity-level risk rating;
generate or file suspicious-activity or regulatory reports; make an actual AML or fraud determination;
or be used on real customer data without a governance-controlled validation and fairness audit.
The positive label is "simulated fraud"; model outputs are "risk scores" and "review priorities".

## Task definition and success metrics

| Item | Definition |
|---|---|
| Unit of analysis | One synthetic financial transaction (one PaySim row) |
| Task type | Binary classification producing a probability-like risk score used for ranking |
| Target | `isFraud` (1 = simulated fraud, 0 = simulated normal) |
| Prediction time | End-of-period batch triage: the transaction's own fields and posted balances are available; aggregates use only strictly earlier transactions |
| Primary technical metric | PR-AUC on the held-out temporal test split |
| Operational metric | Recall@K per review period, K = 200 (about 1% of median daily volume in the validation and test periods, and below the median of 265 positives per test day, so capacity binds) |
| Review period | 24 steps (one simulated day) |
| Secondary metrics | Precision@K, precision, recall, F1, ROC-AUC, confusion matrix at the operating point, PR and calibration curves, Brier, ECE, false-positive rate |
| Business KPI (illustrative) | Positives surfaced within K daily reviews, and the improvement factor versus random selection and a simple rule ranking. Never expressed in currency. |

## Results against the success criteria (single-touch test evaluation, model `20260904T225142-0dc8f82-hgb`)

- SC-001: Recall@200 = **0.7568** (mean over review periods; pooled 95% bootstrap CI [0.7252, 0.7866]) exceeds random ranking (0.1012) and the chronological dummy (0.2076); PR-AUC = **1.0000** exceeds the no-skill value of 0.0109.
- SC-002: the rule comparator (flag, then amount) reaches Recall@200 = 0.3101; the selected model exceeds it.
- Illustrative KPI: 200 positives surfaced per simulated day at K = 200, versus 82 for the rule ranking and 27 for random selection (illustrative counts on synthetic data).

Recall@K is a ceiling set by capacity: every test period holds more than K positives and the top K are
all positives. The near-perfect separability is a property of the PaySim generator (Sections 4–7),
not evidence of real-world AML capability.
