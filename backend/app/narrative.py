"""
Generates a short, plain-language summary of an upload's spending +
detected anomalies via Groq. NOTE (honest simplification): the plan
mentions this endpoint returns "cached" narrative text, but Phase 1's
locked schema (section 7) has no column to persist it in without adding
a new table, which the plan explicitly avoids doing without a real need.
So this currently regenerates fresh on each call rather than caching --
a legitimate follow-up would be adding a nullable `narrative_text` column
to the existing `uploads` table (not a new table) in a later migration.
"""

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-20b"
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set. Check your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def generate_narrative(summary: dict, anomalies: list[dict]) -> str:
    client = _get_client()

    anomaly_lines = "\n".join(
        f"- {a['type']} ({a['severity']}): {a['reason']}" for a in anomalies
    ) or "No anomalies detected this period."

    prompt = f"""Write a short, plain-language monthly financial summary (3-4 sentences)
for a user based on this data. Use the ₹ symbol for all amounts (not $). Be direct and
factual, no fluff, no generic advice.

Total spent: {summary['total_spent']}
Total income: {summary['total_income']}
Spending by category: {summary['by_category']}

Detected issues:
{anomaly_lines}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()