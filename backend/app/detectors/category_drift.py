"""
CategoryDriftDetector: flags a category where the user's total monthly
spend has risen sustainedly compared to their own historical baseline in
that category. Unlike PriceCreepDetector (one merchant getting more
expensive), this catches broader behavioral shifts -- spending more
across an entire category, possibly spread across many different
merchants.

Honest limitation: statistical drift detection on a small sample (~10
baseline months, a handful of transactions per category per month) has
an inherent, nonzero false-positive rate -- a category can randomly run
1.5-2 std deviations above its own baseline by chance alone. We use a
1.5-sigma significance guard alongside the percentage threshold to keep
this reasonable, but it will not be perfect, and shouldn't be expected
to be. Real precision/recall numbers should be reported honestly.
"""

from dataclasses import dataclass, field

import pandas as pd

DRIFT_THRESHOLDS = [
    (50, "HIGH"),
    (25, "MEDIUM"),
]

MIN_BASELINE_MONTHS = 2
RECENT_MONTHS_CHECKED = 2


@dataclass
class Anomaly:
    type: str
    severity: str
    reason: str
    evidence: dict
    transaction_indices: list = field(default_factory=list)


def _severity_for_increase(pct_increase: float) -> str | None:
    for min_pct, severity in DRIFT_THRESHOLDS:
        if pct_increase >= min_pct:
            return severity
    return None


def detect_category_drift(transactions: pd.DataFrame) -> list[Anomaly]:
    """
    transactions must have columns: category, amount, datetime.
    Only considers discretionary categories -- drift in Income/Housing/
    Utilities isn't a "leak," it's just life (rent went up, got a raise).
    """
    anomalies = []
    discretionary = transactions[transactions["category"].isin(
        {"Groceries", "Dining", "Shopping", "Transport"}
    )].copy()

    if discretionary.empty:
        return anomalies

    discretionary["month"] = discretionary["datetime"].dt.to_period("M")
    monthly_totals = (
        discretionary.groupby(["category", "month"])["amount"]
        .apply(lambda s: s.abs().sum())
        .reset_index()
    )

    for category, group in monthly_totals.groupby("category"):
        group_sorted = group.sort_values("month")
        if len(group_sorted) < MIN_BASELINE_MONTHS + 1:
            continue

        recent = group_sorted.tail(RECENT_MONTHS_CHECKED)
        baseline_pool = group_sorted.iloc[: -RECENT_MONTHS_CHECKED]
        if len(baseline_pool) < MIN_BASELINE_MONTHS:
            continue

        baseline = baseline_pool["amount"].median()
        baseline_std = baseline_pool["amount"].std()
        recent_avg = recent["amount"].mean()

        if baseline <= 0:
            continue

        pct_increase = ((recent_avg - baseline) / baseline) * 100
        severity = _severity_for_increase(pct_increase)
        if severity is None:
            continue

        # Statistical-significance guard: require the jump to also clear
        # the category's OWN natural volatility, not just a flat %
        # threshold. Not perfect (see module docstring) but meaningfully
        # reduces noise-driven false positives.
        if pd.notna(baseline_std) and baseline_std > 0:
            if (recent_avg - baseline) < 1.5 * baseline_std:
                continue

        drift_start = recent["month"].iloc[0]
        affected = discretionary[
            (discretionary["category"] == category) & (discretionary["month"] >= drift_start)
        ]

        anomalies.append(Anomaly(
            type="category_drift",
            severity=severity,
            reason=(
                f"{category} spending rose to a monthly average of {recent_avg:.2f}, "
                f"up {pct_increase:.1f}% from a typical {baseline:.2f}/month, "
                f"starting {drift_start}."
            ),
            evidence={
                "category": category,
                "baseline_monthly_avg": round(float(baseline), 2),
                "recent_monthly_avg": round(float(recent_avg), 2),
                "pct_increase": round(float(pct_increase), 1),
                "drift_from": str(drift_start),
            },
            transaction_indices=list(affected.index),
        ))

    return anomalies