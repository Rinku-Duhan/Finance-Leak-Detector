"""
Runs all 4 detectors against every synthetic user and checks results
against ground_truth.json. This is the automated version of the manual
verification done throughout Step 5 -- if a future change to a detector
regresses its accuracy, this is what catches it.
"""

from app.categorizer_rules import rule_based_category
from app.detectors.category_drift import detect_category_drift
from app.detectors.dormant_subscription import detect_dormant_subscriptions
from app.detectors.duplicate import detect_duplicates
from app.detectors.price_creep import detect_price_creep
from app.normalizer import normalize_merchant
from app.parser import parse_csv

DETECTORS = {
    "duplicate_charge": detect_duplicates,
    "dormant_subscription": detect_dormant_subscriptions,
    "price_creep": detect_price_creep,
    "category_drift": detect_category_drift,
}


def _load_df(path):
    with open(path) as f:
        result = parse_csv(f.read())
    df = result.transactions.copy()
    df["normalized_merchant"] = df["description"].apply(normalize_merchant)
    df["category"] = df["normalized_merchant"].apply(lambda m: rule_based_category(m) or "Other")
    return df


def test_all_detectors_against_ground_truth(ground_truth, synthetic_csv_paths):
    grand_expected = 0
    grand_matched = 0
    grand_false_positives = 0

    for user_num, path in synthetic_csv_paths.items():
        df = _load_df(path)
        expected_all = ground_truth[f"user_{user_num}"]["anomalies"]

        for anomaly_type, detector_fn in DETECTORS.items():
            found = detector_fn(df)
            expected = [a for a in expected_all if a["type"] == anomaly_type]

            matched = sum(
                1 for e in expected
                if any(f_.severity == e["expected_severity"] for f_ in found)
            )
            false_positives = max(len(found) - matched, 0)

            grand_expected += len(expected)
            grand_matched += matched
            grand_false_positives += false_positives

    # Known, documented baseline (see category_drift.py docstring): 100%
    # recall, with a small number of honest false positives from natural
    # statistical noise on a small synthetic sample. If recall drops or
    # false positives climb noticeably above this baseline, something
    # regressed and needs investigation.
    assert grand_matched == grand_expected, (
        f"Recall regression: only {grand_matched}/{grand_expected} injected anomalies detected"
    )
    assert grand_false_positives <= 3, (
        f"False positive rate regression: {grand_false_positives} false positives (baseline is 2)"
    )


def test_duplicate_detector_no_false_positives_on_clean_users(synthetic_csv_paths, ground_truth):
    """Users with zero injected duplicates should never produce one."""
    for user_num, path in synthetic_csv_paths.items():
        expected = [
            a for a in ground_truth[f"user_{user_num}"]["anomalies"]
            if a["type"] == "duplicate_charge"
        ]
        if expected:
            continue  # this user IS supposed to have duplicates, skip

        df = _load_df(path)
        found = detect_duplicates(df)
        assert found == [], f"user_{user_num}: unexpected duplicate(s) found where none were injected"


def test_price_creep_ignores_discretionary_categories(synthetic_csv_paths):
    """Regression guard for the bug caught during Step 5: price creep must
    never fire on Groceries/Dining/Shopping/Transport, only Subscriptions/
    Fitness, since discretionary amounts naturally vary a lot."""
    for path in synthetic_csv_paths.values():
        df = _load_df(path)
        found = detect_price_creep(df)
        for anomaly in found:
            merchant_rows = df[df["normalized_merchant"] == anomaly.evidence["merchant"]]
            categories_seen = set(merchant_rows["category"].unique())
            assert categories_seen.issubset({"Subscriptions", "Fitness"}), (
                f"price_creep fired on a discretionary category: {categories_seen}"
            )