"""Project-wide constants. The disclaimer is defined once here and reused verbatim everywhere."""

DISCLAIMER: str = (
    "Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk "
    "scores and review priorities that help human investigators decide what to review first. "
    "This system makes no fraud or AML determination and performs no automatic blocking, "
    "account closure, customer risk rating, or regulatory reporting. Results on synthetic data "
    "do not establish real-world detection effectiveness, fairness, or regulatory suitability."
)

SYNTHETIC_NOTICE: str = (
    "PaySim is synthetic mobile-money transaction data. It is not real SME, corporate, or "
    "Philippine banking data."
)

# The only fields a scoring output may carry (spec FR-081, data-model ReviewQueue).
MODEL_OUTPUT_FIELDS: tuple[str, ...] = (
    "risk_score",
    "review_priority",
    "model_version",
    "disclaimer",
)

# Field names that must never appear in any output surface (constitution Principle IX).
PROHIBITED_OUTPUT_FIELDS: tuple[str, ...] = (
    "allow",
    "block",
    "decision",
    "hold",
    "sar",
    "filing",
    "risk_rating",
    "customer_rating",
    "fraud_confirmed",
)

REVIEW_PRIORITY_LEVELS: tuple[str, ...] = ("high", "medium", "low")

# Process exit codes (contracts/cli-contract.md).
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_VALIDATION = 2
EXIT_GUARD = 3
EXIT_MISSING_PREREQ = 4
