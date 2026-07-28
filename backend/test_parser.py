import sys
sys.path.insert(0, ".")
from app.parser import parse_csv

with open("app/data_gen/output/user_1_transactions.csv") as f:
    result = parse_csv(f.read())

print(f"Total rows: {result.total_rows}, Skipped: {result.skipped_rows}")
print(result.transactions.head())