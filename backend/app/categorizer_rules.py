"""
Rule-based merchant categorization. This is checked *before* the LLM
fallback -- if a merchant clearly matches a known keyword, we never need
to spend an API call on it.
"""

RULE_KEYWORDS: dict[str, list[str]] = {
    "Income": ["SALARY", "CREDIT INTEREST", "REFUND", "CASHBACK"],
    "Housing": ["RENT"],
    "Subscriptions": ["NETFLIX", "SPOTIFY", "AMAZON PRIME", "HOTSTAR", "YOUTUBE PREMIUM", "DISNEY"],
    "Fitness": ["GYM", "CULT FIT", "FITNESS", "CULTFIT"],
    "Utilities": ["ELECTRICITY", "WATER DEPT", "BROADBAND", "AIRTEL", "JIO", "INTERNET", "MOBILE RECHARGE", "WATER BOARD"],
    "Groceries": ["BIGBASKET", "DMART", "ZEPTO", "GROCERY", "SUPERMARKET", "BIG BAZAAR"],
    "Dining": ["SWIGGY", "ZOMATO", "STARBUCKS", "RESTAURANT", "CAFE", "DOMINOS", "PIZZA"],
    "Shopping": ["AMAZON", "MYNTRA", "FLIPKART", "AJIO", "NYKAA"],
    "Transport": ["UBER", "OLA", "IRCTC", "METRO", "FUEL", "PETROL", "RAPIDO"],
}


def rule_based_category(normalized_merchant: str) -> str | None:
    """Returns a category name if a rule matches, else None."""
    merchant = normalized_merchant.upper()
    for category, keywords in RULE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in merchant:
                return category
    return None