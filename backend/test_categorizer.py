import sys, os
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.categorizer import categorize_merchant

db = SessionLocal()

# A merchant that WILL match a rule (should NOT call Groq)
cat, source = categorize_merchant("NETFLIX", db)
print(f"NETFLIX -> {cat} (source: {source.value})")

# A made-up merchant that WON'T match any rule (forces the real Groq call)
cat, source = categorize_merchant("XZQ MYSTERY MART 4471", db)
print(f"XZQ MYSTERY MART 4471 -> {cat} (source: {source.value})")

# Run it again -- should now hit cache, not Groq
cat, source = categorize_merchant("XZQ MYSTERY MART 4471", db)
print(f"XZQ MYSTERY MART 4471 (2nd time) -> {cat} (source: {source.value})")

db.close()