"""
PriceCreepDetector: flags a merchant whose charge amount jumps up
significantly compared to its own recent stable baseline. Only applies to
Subscriptions/Fitness categories -- merchants with an expected FIXED
recurring price. Discretionary categories (Groceries, Dining, Shopping,
Transport) naturally have wildly different amounts per visit, which is
normal variance, not a price hike.
"""

from dataclasses import dataclass, field

import pandas as pd

PRICE_CREEP_THRESHOLDS = [
    (25, "HIGH"),
    (10, "MEDIUM"),
]

MIN_PRIOR_CHARGES = 2
APPLICABLE_CATEGORIES = {"Subscriptions", "Fitness"}


@dataclass
class Anomaly:
    type: str
    severity: str
    reason: str
    evidence: dict
    transaction_indices: list = field(default_factory=list)


def _severity_for_increase(pct_increase: float) -> str | None:
    for min_pct, severity in PRICE_CREEP_THRESHOLDS:
        if pct_increase >= min_pct:
            return severity
    return None


def detect_price_creep(transactions: pd.DataFrame) -> list[Anomaly]:
    anomalies = []

    applicable = transactions[transactions["category"].isin(APPLICABLE_CATEGORIES)]

    for merchant, group in applicable.groupby("normalized_merchant"):
        if len(group) < MIN_PRIOR_CHARGES + 1:
            continue

        group_sorted = group.sort_values("datetime").reset_index()
        amounts = group_sorted["amount"].abs()

        flagged_already = False

        for i in range(MIN_PRIOR_CHARGES, len(group_sorted)):
            if flagged_already:
                break

            prior_amounts = amounts.iloc[max(0, i - 3):i]
            baseline = prior_amounts.median()
            current = amounts.iloc[i]

            if baseline <= 0:
                continue

            pct_increase = ((current - baseline) / baseline) * 100
            severity = _severity_for_increase(pct_increase)
            if severity is None:
                continue

            row = group_sorted.iloc[i]
            anomalies.append(Anomaly(
                type="price_creep",
                severity=severity,
                reason=(
                    f"{merchant} charge increased from a typical {baseline:.2f} to "
                    f"{current:.2f} ({pct_increase:.1f}% increase)."
                ),
                evidence={
                    "merchant": merchant,
                    "old_amount": round(float(baseline), 2),
                    "new_amount": round(float(current), 2),
                    "pct_increase": round(float(pct_increase), 1),
                    "effective_from": row["datetime"].isoformat(),
                },
                transaction_indices=[row["index"]],
            ))
            flagged_already = True

    return anomalies