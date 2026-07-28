"""
DormantSubscriptionDetector: flags subscription/fitness-category merchants
charged consistently for many consecutive months.

Honest limitation: this only proves the charge kept recurring -- it does
NOT prove the user stopped using the service, since we have no
usage/login data, only transactions. We frame findings as "worth
reviewing," not "confirmed unused."
"""

from dataclasses import dataclass, field

import pandas as pd

SUBSCRIPTION_CATEGORIES = {"Subscriptions", "Fitness"}

DORMANT_THRESHOLDS = [
    (10, "HIGH"),
    (6, "MEDIUM"),
    (3, "LOW"),
]


@dataclass
class Anomaly:
    type: str
    severity: str
    reason: str
    evidence: dict
    transaction_indices: list = field(default_factory=list)


def _severity_for_streak(months: int) -> str | None:
    for min_months, severity in DORMANT_THRESHOLDS:
        if months >= min_months:
            return severity
    return None


def _longest_consecutive_month_streak(month_periods: list) -> tuple[int, list]:
    if not month_periods:
        return 0, []

    months_sorted = sorted(set(month_periods))
    best_streak = [months_sorted[0]]
    current_streak = [months_sorted[0]]

    for prev, curr in zip(months_sorted, months_sorted[1:]):
        if curr == prev + 1:
            current_streak.append(curr)
        else:
            current_streak = [curr]
        if len(current_streak) > len(best_streak):
            best_streak = current_streak

    return len(best_streak), best_streak


def detect_dormant_subscriptions(transactions: pd.DataFrame) -> list[Anomaly]:
    anomalies = []

    subs_df = transactions[transactions["category"].isin(SUBSCRIPTION_CATEGORIES)]

    for merchant, group in subs_df.groupby("normalized_merchant"):
        months = group["datetime"].dt.to_period("M").tolist()
        streak_len, streak_months = _longest_consecutive_month_streak(months)

        severity = _severity_for_streak(streak_len)
        if severity is None:
            continue

        in_streak = group[group["datetime"].dt.to_period("M").isin(streak_months)]
        avg_amount = round(in_streak["amount"].mean(), 2)

        anomalies.append(Anomaly(
            type="dormant_subscription",
            severity=severity,
            reason=(
                f"{merchant} has been charged for {streak_len} consecutive months "
                f"(avg {abs(avg_amount):.2f} per charge) -- worth reviewing whether "
                f"it's still being used."
            ),
            evidence={
                "merchant": merchant,
                "consecutive_months_charged": streak_len,
                "avg_amount": abs(float(avg_amount)),
                "streak_start": str(streak_months[0]),
                "streak_end": str(streak_months[-1]),
            },
            transaction_indices=list(in_streak.index),
        ))

    return anomalies