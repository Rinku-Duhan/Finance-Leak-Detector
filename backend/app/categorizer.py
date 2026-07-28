"""
Categorize stage. Priority order (per plan section 6):
    1. merchant_category cache (DB) -- fastest, free
    2. rule-based keyword match -- fast, free, deterministic
    3. Groq LLM fallback -- only for merchants neither of the above caught

Whichever tier resolves the category gets written back to the cache, so
the *same* merchant never needs the LLM twice.
"""

import os

from dotenv import load_dotenv
from groq import Groq
from sqlalchemy.orm import Session

from app.categorizer_rules import rule_based_category
from app.models import CategorySource, MerchantCategory

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-20b"  # small/fast model -- categorization is a simple task

VALID_CATEGORIES = [
    "Income", "Housing", "Subscriptions", "Fitness", "Utilities",
    "Groceries", "Dining", "Shopping", "Transport", "Other",
]

_groq_client = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set. Check your .env file.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def llm_categorize(normalized_merchant: str) -> str:
    """Ask Groq to classify an unknown merchant into one of our fixed categories."""
    client = _get_groq_client()

    system_prompt = (
        "You are a financial transaction categorizer. Given a merchant name, "
        "respond with EXACTLY ONE category from this list, nothing else, no "
        "explanation:\n" + ", ".join(VALID_CATEGORIES)
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Merchant: {normalized_merchant}"},
        ],
        temperature=0,
        max_tokens=10,
    )

    raw_answer = response.choices[0].message.content.strip()

    for category in VALID_CATEGORIES:
        if category.lower() in raw_answer.lower():
            return category

    return "Other"


def _get_cached_category(db: Session, normalized_merchant: str) -> str | None:
    row = db.query(MerchantCategory).filter(
        MerchantCategory.normalized_merchant == normalized_merchant
    ).first()
    return row.category if row else None


def _write_cache(db: Session, normalized_merchant: str, category: str) -> None:
    entry = MerchantCategory(normalized_merchant=normalized_merchant, category=category)
    db.add(entry)
    db.commit()


def categorize_merchant(normalized_merchant: str, db: Session) -> tuple[str, CategorySource]:
    """Returns (category, source) where source tells you which tier resolved it."""

    cached = _get_cached_category(db, normalized_merchant)
    if cached is not None:
        return cached, CategorySource.CACHE

    rule_match = rule_based_category(normalized_merchant)
    if rule_match is not None:
        _write_cache(db, normalized_merchant, rule_match)
        return rule_match, CategorySource.RULE

    llm_result = llm_categorize(normalized_merchant)
    _write_cache(db, normalized_merchant, llm_result)
    return llm_result, CategorySource.LLM