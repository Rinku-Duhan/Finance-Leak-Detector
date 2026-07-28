import pytest

from app.categorizer_rules import rule_based_category


@pytest.mark.parametrize("merchant,expected_category", [
    ("SALARY CREDIT", "Income"),
    ("RENT PAYMENT", "Housing"),
    ("NETFLIX", "Subscriptions"),
    ("AMAZON PRIME", "Subscriptions"),
    ("CULT FIT GYM", "Fitness"),
    ("ELECTRICITY BOARD", "Utilities"),
    ("AIRTEL BROADBAND", "Utilities"),
    ("BIGBASKET", "Groceries"),
    ("DMART", "Groceries"),
    ("SWIGGY", "Dining"),
    ("ZOMATO", "Dining"),
    ("STARBUCKS", "Dining"),
    ("AMAZON", "Shopping"),
    ("MYNTRA", "Shopping"),
    ("FLIPKART", "Shopping"),
    ("UBER", "Transport"),
    ("OLA", "Transport"),
    ("IRCTC", "Transport"),
])
def test_rule_based_category(merchant, expected_category):
    assert rule_based_category(merchant) == expected_category


def test_unknown_merchant_returns_none():
    assert rule_based_category("SOME COMPLETELY UNKNOWN MERCHANT XYZ") is None


def test_all_synthetic_merchants_categorized_by_rules(synthetic_csv_paths):
    """Every merchant our own generator produces should be resolvable by
    rules alone -- if this ever fails, either a new merchant was added to
    the generator without a matching rule, or a rule regressed."""
    from app.normalizer import normalize_merchant
    from app.parser import parse_csv

    for path in synthetic_csv_paths.values():
        with open(path) as f:
            result = parse_csv(f.read())
        for desc in result.transactions["description"].unique():
            normalized = normalize_merchant(desc)
            category = rule_based_category(normalized)
            assert category is not None, f"{normalized!r} has no matching rule"