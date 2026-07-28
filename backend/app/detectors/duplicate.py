"""
DuplicateDetector: flags pairs of transactions from the same user with the
same normalized merchant and the exact same amount, occurring close
together in time. Severity scales with how close together they are --
closer together is more likely a technical glitch (POS double-swipe,
billing retry) than a coincidence.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

DUPLICATE_THRESHOLDS = [
    (6, "HIGH"),
    (24, "MEDIUM"),
    (72, "LOW"),
]


@dataclass
class Anomaly:
    type: str
    severity: str
    reason: str
    evidence: dict
    transaction_indices: list = field(default_factory=list)


def _severity_for_gap(hours_apart: float) -> str | None:
    for max_hours, severity in DUPLICATE_THRESHOLDS:
        if hours_apart <= max_hours:
            return severity
    return None


def detect_duplicates(transactions: pd.DataFrame) -> list[Anomaly]:
    anomalies = []
    already_paired = set()

    grouped = transactions.groupby(["normalized_merchant", "amount"])

    for (merchant, amount), group in grouped:
        if len(group) < 2:
            continue

        group_sorted = group.sort_values("datetime")
        rows = list(group_sorted.itertuples())

        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if a.Index in already_paired or b.Index in already_paired:
                continue

            gap_hours = (b.datetime - a.datetime).total_seconds() / 3600.0
            severity = _severity_for_gap(gap_hours)
            if severity is None:
                continue

            already_paired.add(a.Index)
            already_paired.add(b.Index)

            anomalies.append(Anomaly(
                type="duplicate_charge",
                severity=severity,
                reason=(
                    f"Same charge of {amount} at {merchant} occurred twice, "
                    f"{gap_hours:.1f} hours apart."
                ),
                evidence={
                    "merchant": merchant,
                    "amount": float(amount),
                    "hours_apart": round(gap_hours, 2),
                    "first_datetime": a.datetime.isoformat(),
                    "second_datetime": b.datetime.isoformat(),
                },
                transaction_indices=[a.Index, b.Index],
            ))

    return anomalies