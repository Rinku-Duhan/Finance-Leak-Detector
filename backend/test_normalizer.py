import sys
sys.path.insert(0, ".")
from app.normalizer import normalize_merchant

tests = ["NETFLIX.COM 4085604485", "NETFLIX INDIA", "POS 1234 STARBUCKS MUMBAI IN", "AMZN MKTP IN"]
for t in tests:
    print(f"{t:35} -> {normalize_merchant(t)}")