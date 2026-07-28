"""
Normalize stage: turns messy raw transaction descriptions into a clean,
canonical merchant name -- e.g.:
    "NETFLIX.COM 4085604485"            -> "NETFLIX"
    "UPI-SWIGGY-swiggy@ybl-YESB0000..." -> "SWIGGY"
    "POS 1234 STARBUCKS MUMBAI IN"      -> "STARBUCKS"
"""

import re

# Payment-rail / transaction-mechanism prefixes that carry no merchant info.
NOISE_PREFIXES = [
    "UPI", "POS", "NEFT", "IMPS", "ACH", "RTGS", "ECS",
    "TXN", "PURCHASE AT", "PAYMENT TO", "PAID TO", "DEBIT CARD", "CREDIT CARD",
]

# Common Indian city/state names that show up appended to merchant names.
CITY_NOISE = [
    "MUMBAI", "DELHI", "BANGALORE", "BENGALURU", "HYDERABAD", "CHENNAI",
    "KOLKATA", "PUNE", "AHMEDABAD", "SURAT", "JAIPUR", "LUCKNOW", "GURGAON",
    "GURUGRAM", "NOIDA", "INDIA", "IN",
]

# Corporate suffixes that add no identifying info.
CORP_SUFFIXES = ["PVT LTD", "PRIVATE LIMITED", "LTD", "LIMITED", "LLC", "INC", "CO"]

# Known merchant aliases: canonical name -> substrings that indicate it.
# This is what collapses "AMZN MKTP IN", "AMAZON.COM", "AMAZON PAY" all to
# one canonical merchant, which is what makes price-creep / duplicate
# detection reliable downstream.
MERCHANT_ALIASES = {
    "AMAZON PRIME": ["AMAZON PRIME", "PRIME VIDEO"],
    "AMAZON": ["AMZN", "AMAZON"],
    "NETFLIX": ["NETFLIX"],
    "SPOTIFY": ["SPOTIFY"],
    "SWIGGY": ["SWIGGY"],
    "ZOMATO": ["ZOMATO"],
    "UBER": ["UBER"],
    "OLA": ["OLA CABS", "OLA"],
    "MYNTRA": ["MYNTRA"],
    "FLIPKART": ["FLIPKART", "FKRT"],
    "STARBUCKS": ["STARBUCKS"],
    "BIGBASKET": ["BIGBASKET", "BIG BASKET"],
    "DMART": ["DMART", "D MART"],
    "ZEPTO": ["ZEPTO"],
    "IRCTC": ["IRCTC"],
    "CULT FIT GYM": ["CULT FIT", "CULTFIT"],
}

_REFERENCE_NUMBER_RE = re.compile(r"\b\d{5,}\b")  # long numeric IDs (txn refs, phone-ish codes)
_SPECIAL_CHARS_RE = re.compile(r"[^A-Z0-9 ]")
_MULTI_SPACE_RE = re.compile(r"\s+")


def normalize_merchant(raw_description: str) -> str:
    if not raw_description or not raw_description.strip():
        return "UNKNOWN"

    text = raw_description.upper().strip()

    # Replace separators (-, _, /, *, .) with spaces so tokens split cleanly
    text = re.sub(r"[-_/*.]", " ", text)

    # Strip long numeric reference numbers / transaction IDs
    text = _REFERENCE_NUMBER_RE.sub(" ", text)

    # Strip non-alphanumeric noise
    text = _SPECIAL_CHARS_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()

    # Remove payment-rail prefixes (only if truly at the start)
    for prefix in NOISE_PREFIXES:
        if text.startswith(prefix + " "):
            text = text[len(prefix):].strip()

    tokens = text.split()

    # Remove city/state/country noise tokens and corporate suffix tokens
    corp_suffix_tokens = set(" ".join(CORP_SUFFIXES).split())
    tokens = [t for t in tokens if t not in CITY_NOISE and t not in corp_suffix_tokens]

    cleaned = " ".join(tokens).strip()

    if not cleaned:
        return "UNKNOWN"

    # Canonical alias matching: if any known merchant alias appears in the
    # cleaned text, collapse to that canonical name.
    for canonical, aliases in MERCHANT_ALIASES.items():
        for alias in aliases:
            if alias in cleaned:
                return canonical

    return cleaned