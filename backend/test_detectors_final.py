import sys, json
sys.path.insert(0, ".")

from app.parser import parse_csv
from app.normalizer import normalize_merchant
from app.categorizer_rules import rule_based_category
from app.detectors.duplicate import detect_duplicates
from app.detectors.dormant_subscription import detect_dormant_subscriptions
from app.detectors.price_creep import detect_price_creep
from app.detectors.category_drift import detect_category_drift

with open("app/data_gen/output/ground_truth.json") as f:
    ground_truth = json.load(f)

def load_df(user_num):
    with open(f"app/data_gen/output/user_{user_num}_transactions.csv") as f:
        result = parse_csv(f.read())
    df = result.transactions.copy()
    df["normalized_merchant"] = df["description"].apply(normalize_merchant)
    df["category"] = df["normalized_merchant"].apply(lambda m: rule_based_category(m) or "Other")
    return df

detectors = {
    "duplicate_charge": detect_duplicates,
    "dormant_subscription": detect_dormant_subscriptions,
    "price_creep": detect_price_creep,
    "category_drift": detect_category_drift,
}

grand_expected, grand_matched, grand_fp = 0, 0, 0
for user_num in range(1, 9):
    df = load_df(user_num)
    expected_all = ground_truth[f"user_{user_num}"]["anomalies"]
    for atype, fn in detectors.items():
        found = fn(df)
        expected = [a for a in expected_all if a["type"] == atype]
        matched = sum(1 for e in expected if any(f_.severity == e["expected_severity"] for f_ in found))
        fp = len(found) - matched
        grand_expected += len(expected)
        grand_matched += matched
        grand_fp += max(fp, 0)
        if expected or found:
            print(f"user_{user_num} {atype:22} expected={len(expected)} found={len(found)} matched={matched} fp={fp}")

print(f"\nGRAND TOTAL: {grand_matched}/{grand_expected} matched, {grand_fp} false positives")