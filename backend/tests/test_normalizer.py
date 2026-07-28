import pytest

from app.normalizer import normalize_merchant


@pytest.mark.parametrize("raw,expected", [
    ("NETFLIX.COM 4085604485", "NETFLIX"),
    ("NETFLIX INDIA", "NETFLIX"),
    ("NETFLIX MUMBAI", "NETFLIX"),
    ("POS 1234 STARBUCKS MUMBAI IN", "STARBUCKS"),
    ("AMZN MKTP IN", "AMAZON"),
    ("AMAZON.COM", "AMAZON"),
    ("AMAZON PRIME VIDEO SUBSCRIPTION", "AMAZON PRIME"),
    ("SWIGGY*ORDER1234", "SWIGGY"),
    ("ZOMATO PVT LTD BANGALORE", "ZOMATO"),
    ("CULT.FIT GYM MEMBERSHIP 998877", "CULT FIT GYM"),
    ("SALARY CREDIT", "SALARY CREDIT"),
    ("RENT PAYMENT", "RENT PAYMENT"),
    ("", "UNKNOWN"),
    ("   ", "UNKNOWN"),
    ("123456789", "UNKNOWN"),
])
def test_normalize_merchant(raw, expected):
    assert normalize_merchant(raw) == expected


def test_upi_reference_number_stripped():
    raw = "UPI-SWIGGY-swiggy@ybl-YESB0000001-123456789012-payment".upper()
    assert normalize_merchant(raw) == "SWIGGY"


def test_all_synthetic_merchants_normalize_without_corruption(synthetic_csv_paths):
    """Real merchant names from our own generator should pass through
    unchanged -- confirms the normalizer isn't over-aggressive on already
    clean input."""
    from app.parser import parse_csv

    for path in synthetic_csv_paths.values():
        with open(path) as f:
            result = parse_csv(f.read())
        for desc in result.transactions["description"].unique():
            normalized = normalize_merchant(desc)
            assert normalized != "UNKNOWN", f"{desc!r} should not normalize to UNKNOWN"