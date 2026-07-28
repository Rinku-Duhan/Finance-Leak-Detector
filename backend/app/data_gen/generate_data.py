"""
Synthetic transaction data generator for Finance Leak Detector.
Generates realistic bank-style CSVs for N users over M months,
with deliberately injected anomalies + a ground_truth.json for scoring.

v2 change: subscriptions now have realistic, variable lifespans (most
cancel after a couple of months, like real people actually do) instead of
running unconditionally for the entire window. This is what makes
DormantSubscriptionDetector's "N consecutive months" signal meaningful --
without variety, EVERY subscription for EVERY user would look "dormant,"
which taught us nothing. Dormant-subscription ground truth is now
auto-derived using the exact same threshold function the real detector
uses, so the answer key can never silently drift out of sync with it.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

NUM_USERS = 8
MONTHS = 12
END_DATE = datetime(2026, 6, 30)
START_DATE = END_DATE - timedelta(days=30 * MONTHS)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CATEGORIES = {
    "Income": ["SALARY CREDIT"],
    "Housing": ["RENT PAYMENT"],
    "Subscriptions": ["NETFLIX", "SPOTIFY", "AMAZON PRIME"],
    "Fitness": ["CULT FIT GYM"],
    "Utilities": ["ELECTRICITY BOARD", "WATER DEPT", "AIRTEL BROADBAND"],
    "Groceries": ["BIGBASKET", "DMART", "ZEPTO"],
    "Dining": ["SWIGGY", "ZOMATO", "STARBUCKS"],
    "Shopping": ["AMAZON", "MYNTRA", "FLIPKART"],
    "Transport": ["UBER", "OLA", "IRCTC"],
}

# Same thresholds as app/detectors/dormant_subscription.py -- kept in sync
# deliberately so ground truth always matches the real detector's logic.
DORMANT_THRESHOLDS = [
    (10, "HIGH"),
    (6, "MEDIUM"),
    (3, "LOW"),
]


def severity_for_streak(months: int) -> str | None:
    for min_months, severity in DORMANT_THRESHOLDS:
        if months >= min_months:
            return severity
    return None


def month_range(start, end):
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        months.append(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def random_time_on(date):
    return date.replace(
        hour=random.randint(7, 22), minute=random.randint(0, 59), second=random.randint(0, 59)
    )


def build_base_transactions(user_id, sub_durations: dict):
    """
    Build a normal M-month transaction history for one user.

    sub_durations: dict mapping each of "NETFLIX", "SPOTIFY", "AMAZON PRIME",
    "CULT FIT GYM" -> number of months (from the start of the window) that
    subscription stays active before being cancelled. A duration >= MONTHS
    means "never cancelled, runs the whole window."
    """
    rows = []
    months = month_range(START_DATE, END_DATE)

    salary = round(random.uniform(45000, 90000), 2)
    rent = round(random.uniform(12000, 25000), 2)
    subs = {name: round(random.uniform(150, 700), 2) for name in CATEGORIES["Subscriptions"]}
    gym_amount = round(random.uniform(1200, 2500), 2)
    utility_base = {name: round(random.uniform(600, 2000), 2) for name in CATEGORIES["Utilities"]}

    tx_id = 0

    def add(date, merchant, amount, category, tx_type):
        nonlocal tx_id
        tx_id += 1
        rows.append(
            {
                "tx_ref": f"u{user_id}_t{tx_id}",
                "datetime": date,
                "description": merchant,
                "amount": round(amount, 2),
                "type": tx_type,
                "category_truth": category,
            }
        )
        return rows[-1]["tx_ref"]

    for month_idx, m in enumerate(months):
        add(random_time_on(m.replace(day=1)), "SALARY CREDIT", salary, "Income", "CREDIT")
        add(random_time_on(m.replace(day=3)), "RENT PAYMENT", rent, "Housing", "DEBIT")

        for name, amt in subs.items():
            if month_idx < sub_durations.get(name, 2):
                add(random_time_on(m.replace(day=random.randint(4, 8))), name, amt, "Subscriptions", "DEBIT")

        if month_idx < sub_durations.get("CULT FIT GYM", 2):
            add(random_time_on(m.replace(day=random.randint(4, 8))), "CULT FIT GYM", gym_amount, "Fitness", "DEBIT")

        for name, amt in utility_base.items():
            variance = amt * random.uniform(-0.08, 0.08)
            add(random_time_on(m.replace(day=random.randint(9, 15))), name, amt + variance, "Utilities", "DEBIT")

        category_counts = {
            "Groceries": random.randint(4, 7),
            "Dining": random.randint(3, 6),
            "Shopping": random.randint(2, 4),
            "Transport": random.randint(3, 5),
        }
        amount_ranges = {
            "Groceries": (400, 1800),
            "Dining": (200, 800),
            "Shopping": (800, 3000),
            "Transport": (80, 500),
        }
        for cat, count in category_counts.items():
            for _ in range(count):
                merchant = random.choice(CATEGORIES[cat])
                day = random.randint(1, 28)
                low, high = amount_ranges[cat]
                amt = random.uniform(low, high)
                add(random_time_on(m.replace(day=day)), merchant, amt, cat, "DEBIT")

    return rows, {"subs": subs, "months": months}


def inject_duplicate(rows, hours_apart, severity):
    candidates = [r for r in rows if r["category_truth"] in ("Groceries", "Dining", "Shopping")]
    original = random.choice(candidates)
    dup_time = original["datetime"] + timedelta(hours=hours_apart)
    new_ref = f"{original['tx_ref']}_dup"
    dup = dict(original)
    dup["tx_ref"] = new_ref
    dup["datetime"] = dup_time
    rows.append(dup)
    return {
        "type": "duplicate_charge",
        "expected_severity": severity,
        "transaction_refs": [original["tx_ref"], new_ref],
        "evidence": {
            "merchant": original["description"],
            "amount": original["amount"],
            "hours_apart": hours_apart,
        },
    }


def inject_price_creep(rows, context, pct_increase, severity, sub_name):
    """Bump `sub_name`'s price from the halfway point of the window onward.
    sub_name must be a subscription that stays active for the FULL window
    (see sub_durations) so there's a real "before" and "after" to compare."""
    months = context["months"]
    jump_month = months[len(months) // 2]
    old_amount = context["subs"][sub_name]
    new_amount = round(old_amount * (1 + pct_increase / 100), 2)

    affected_refs = []
    for r in rows:
        if r["description"] == sub_name and r["datetime"] >= jump_month:
            r["amount"] = new_amount
            affected_refs.append(r["tx_ref"])

    return {
        "type": "price_creep",
        "expected_severity": severity,
        "transaction_refs": affected_refs,
        "evidence": {
            "merchant": sub_name,
            "old_amount": old_amount,
            "new_amount": new_amount,
            "pct_increase": pct_increase,
            "effective_from": jump_month.strftime("%Y-%m-%d"),
        },
    }


def inject_category_drift(rows, context, target_pct_increase, severity, category="Dining"):
    """
    Precisely scales the last 2 months of `category` spending so the
    resulting increase vs. baseline lands reliably in the intended
    severity band -- random per-transaction multipliers were too noisy to
    hit a specific target with only ~3-5 transactions/month.
    """
    months = context["months"]
    drift_months = months[-2:]

    # Baseline: median monthly total for this category, from all months
    # BEFORE the drift window (matches how the real detector computes it).
    baseline_months = months[:-2]
    monthly_totals = {}
    for r in rows:
        if r["category_truth"] == category:
            month_key = r["datetime"].replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_totals.setdefault(month_key, 0.0)
            monthly_totals[month_key] += abs(r["amount"])

    baseline_values = [monthly_totals.get(m, 0.0) for m in baseline_months]
    baseline_values = sorted(v for v in baseline_values if v > 0)
    baseline = baseline_values[len(baseline_values) // 2] if baseline_values else 0.0

    target_recent_avg = baseline * (1 + target_pct_increase / 100)

    recent_rows = [r for r in rows if r["category_truth"] == category and r["datetime"] >= drift_months[0]]
    current_recent_avg = sum(abs(r["amount"]) for r in recent_rows) / 2  # 2 months

    if current_recent_avg <= 0:
        scale_factor = 1.0
    else:
        scale_factor = target_recent_avg / current_recent_avg

    affected_refs = []
    for r in recent_rows:
        r["amount"] = round(r["amount"] * scale_factor, 2)
        affected_refs.append(r["tx_ref"])

    return {
        "type": "category_drift",
        "expected_severity": severity,
        "transaction_refs": affected_refs,
        "evidence": {
            "category": category,
            "drift_from": drift_months[0].strftime("%Y-%m-%d"),
            "target_pct_increase": target_pct_increase,
        },
    }


def derive_dormant_ground_truth(rows, sub_durations):
    """
    Auto-generate dormant_subscription ground truth entries directly from
    the actual sub_durations used to build this user's data -- using the
    SAME threshold function the real detector uses. This guarantees the
    ground truth can never drift out of sync with detector logic,
    including "side effect" dormant flags on a subscription that was ALSO
    used for price creep (a subscription forced to run the full window for
    price-creep realism will legitimately also look dormant -- that's a
    real, honest overlap, not a bug).
    """
    entries = []
    for merchant, duration in sub_durations.items():
        streak = min(duration, MONTHS)
        severity = severity_for_streak(streak)
        if severity is None:
            continue
        refs = [r["tx_ref"] for r in rows if r["description"] == merchant]
        entries.append({
            "type": "dormant_subscription",
            "expected_severity": severity,
            "transaction_refs": refs,
            "evidence": {
                "merchant": merchant,
                "consecutive_months_charged": streak,
                "note": "Auto-derived from sub_durations using detector's own threshold logic.",
            },
        })
    return entries


# Per-user subscription lifespan plans. "SHORT" = cancelled early (2 months),
# never enough to trigger dormant detection. Explicit numbers = deliberately
# controlled duration to hit a target severity band, or MONTHS (full window)
# where a subscription needs to survive a price-creep jump partway through.
SHORT = 2

USER_SUB_PLANS = {
    1: {"NETFLIX": SHORT, "SPOTIFY": SHORT, "AMAZON PRIME": SHORT, "CULT FIT GYM": SHORT},
    2: {"NETFLIX": SHORT, "SPOTIFY": SHORT, "AMAZON PRIME": MONTHS, "CULT FIT GYM": SHORT},
    3: {"NETFLIX": SHORT, "SPOTIFY": 7, "AMAZON PRIME": SHORT, "CULT FIT GYM": SHORT},
    4: {"NETFLIX": SHORT, "SPOTIFY": SHORT, "AMAZON PRIME": SHORT, "CULT FIT GYM": SHORT},
    5: {"NETFLIX": SHORT, "SPOTIFY": SHORT, "AMAZON PRIME": MONTHS, "CULT FIT GYM": SHORT},
    6: {"NETFLIX": 8, "SPOTIFY": SHORT, "AMAZON PRIME": SHORT, "CULT FIT GYM": SHORT},
    7: {"NETFLIX": SHORT, "SPOTIFY": 4, "AMAZON PRIME": MONTHS, "CULT FIT GYM": SHORT},
    8: {"NETFLIX": SHORT, "SPOTIFY": SHORT, "AMAZON PRIME": MONTHS, "CULT FIT GYM": SHORT},
}


def main():
    ground_truth = {}

    for user_id in range(1, NUM_USERS + 1):
        sub_plan = USER_SUB_PLANS[user_id]
        rows, context = build_base_transactions(user_id, sub_plan)
        anomalies = []

        if user_id == 1:
            anomalies.append(inject_duplicate(rows, hours_apart=3, severity="HIGH"))
        elif user_id == 2:
            anomalies.append(inject_price_creep(rows, context, pct_increase=30, severity="HIGH", sub_name="AMAZON PRIME"))
        elif user_id == 3:
            pass  # dormant ground truth auto-derived below
        elif user_id == 4:
            anomalies.append(inject_category_drift(rows, context, target_pct_increase=90, severity="HIGH", category="Shopping"))
        elif user_id == 5:
            anomalies.append(inject_duplicate(rows, hours_apart=20, severity="MEDIUM"))
            anomalies.append(inject_price_creep(rows, context, pct_increase=15, severity="MEDIUM", sub_name="AMAZON PRIME"))
        elif user_id == 6:
            anomalies.append(inject_category_drift(rows, context, target_pct_increase=80, severity="HIGH", category="Dining"))
        elif user_id == 7:
            anomalies.append(inject_duplicate(rows, hours_apart=4, severity="HIGH"))
            anomalies.append(inject_price_creep(rows, context, pct_increase=40, severity="HIGH", sub_name="AMAZON PRIME"))
        elif user_id == 8:
            anomalies.append(inject_category_drift(rows, context, target_pct_increase=44, severity="MEDIUM", category="Dining"))
            anomalies.append(inject_duplicate(rows, hours_apart=24, severity="MEDIUM"))
            anomalies.append(inject_price_creep(rows, context, pct_increase=12, severity="MEDIUM", sub_name="AMAZON PRIME"))

        # Auto-derive dormant_subscription ground truth from actual sub_durations
        anomalies.extend(derive_dormant_ground_truth(rows, sub_plan))

        rows.sort(key=lambda r: r["datetime"])

        df = pd.DataFrame(rows)
        export_df = df[["datetime", "description", "amount", "type"]].copy()
        export_df["datetime"] = export_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        export_df.columns = ["Date", "Description", "Amount", "Type"]

        csv_path = OUTPUT_DIR / f"user_{user_id}_transactions.csv"
        export_df.to_csv(csv_path, index=False)

        ground_truth[f"user_{user_id}"] = {
            "num_transactions": len(rows),
            "anomalies": anomalies,
        }

        print(f"user_{user_id}: {len(rows)} transactions, {len(anomalies)} injected anomalies -> {csv_path.name}")

    gt_path = OUTPUT_DIR / "ground_truth.json"
    with open(gt_path, "w") as f:
        json.dump(ground_truth, f, indent=2, default=str)

    print(f"\nGround truth written to {gt_path}")


if __name__ == "__main__":
    main()