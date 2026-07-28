import sys, json
sys.path.insert(0, ".")

from app.parser import parse_csv
from app.normalizer import normalize_merchant
from app.categorizer_rules import rule_based_category
from app.detectors.duplicate import detect_duplicates
from app.detectors.dormant_subscription import detect_dormant_subscriptions
from app.detectors.price_creep import detect_price_creep

with open("app/data_gen/output/ground_truth.json") as f:
    ground_truth = json.load(f)

for user_num in range(1, 9):
    with open(f"app/data_gen/output/user_{user_num}_transactions.csv") as f:
        result = parse_csv(f.read())
    df = result.transactions.copy()
    df["normalized_merchant"] = df["description"].apply(normalize_merchant)
    df["category"] = df["normalized_merchant"].apply(lambda m: rule_based_category(m) or "Other")

    dups = detect_duplicates(df)
    dormant = detect_dormant_subscriptions(df)
    creep = detect_price_creep(df)

    expected = ground_truth[f"user_{user_num}"]["anomalies"]
    print(f"user_{user_num}: expected={len(expected)} | found dup={len(dups)} dormant={len(dormant)} creep={len(creep)}")

print("\nDone -- compare counts above against your ground_truth.json anomaly counts per user.")