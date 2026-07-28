"""
Parse stage: reads a raw bank/UPI CSV export (varying column names/formats
across banks) into a standard internal shape:

    datetime (pd.Timestamp), description (str), amount (float, signed:
    negative = money out / DEBIT, positive = money in / CREDIT)

Rows that can't be parsed (bad dates, non-numeric amounts, missing
required fields) are skipped, not fatal -- a real bank export can have
a stray footer row, a blank line, a currency symbol, etc.
"""

import io
from dataclasses import dataclass, field

import pandas as pd

# Column name aliases seen across different bank export formats.
# All matching is case-insensitive and whitespace-stripped.
DATE_ALIASES = {"date", "transaction date", "txn date", "value date", "posting date"}
DESC_ALIASES = {"description", "narration", "particulars", "merchant", "details", "remarks"}
AMOUNT_ALIASES = {"amount", "transaction amount", "txn amount"}
DEBIT_ALIASES = {"debit", "withdrawal", "debit amount", "withdrawal amt"}
CREDIT_ALIASES = {"credit", "deposit", "credit amount", "deposit amt"}
TYPE_ALIASES = {"type", "transaction type", "txn type", "dr/cr"}


@dataclass
class ParseResult:
    transactions: pd.DataFrame
    total_rows: int
    skipped_rows: int
    skip_reasons: list = field(default_factory=list)


def _normalize_columns(df: pd.DataFrame) -> dict:
    """Map this file's actual column names to our standard roles."""
    colmap = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in DATE_ALIASES:
            colmap["date"] = col
        elif key in DESC_ALIASES:
            colmap["description"] = col
        elif key in AMOUNT_ALIASES:
            colmap["amount"] = col
        elif key in DEBIT_ALIASES:
            colmap["debit"] = col
        elif key in CREDIT_ALIASES:
            colmap["credit"] = col
        elif key in TYPE_ALIASES:
            colmap["type"] = col
    return colmap


def parse_csv(file_content: bytes | str) -> ParseResult:
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8", errors="replace")

    raw_df = pd.read_csv(io.StringIO(file_content), dtype=str, keep_default_na=False)
    raw_df.columns = [c.strip() for c in raw_df.columns]
    colmap = _normalize_columns(raw_df)

    if "date" not in colmap or "description" not in colmap:
        raise ValueError(
            "Could not find required 'date' and 'description' columns. "
            f"Found columns: {list(raw_df.columns)}"
        )

    has_single_amount = "amount" in colmap and "type" in colmap
    has_split_amount = "debit" in colmap or "credit" in colmap

    if not has_single_amount and not has_split_amount:
        raise ValueError(
            "Could not find amount columns. Expected either an 'Amount' + 'Type' "
            "pair, or separate 'Debit'/'Credit' columns."
        )

    records = []
    skipped = 0
    skip_reasons = []

    for idx, row in raw_df.iterrows():
        try:
            date_val = pd.to_datetime(row[colmap["date"]], errors="raise")
            if pd.isna(date_val):
                raise ValueError("missing/unparseable date")
            description = str(row[colmap["description"]]).strip()
            if not description:
                raise ValueError("empty description")

            if has_single_amount:
                raw_amount = _clean_amount(row[colmap["amount"]])
                txn_type = str(row[colmap["type"]]).strip().upper()
                signed_amount = -abs(raw_amount) if txn_type.startswith("D") else abs(raw_amount)
            else:
                debit_raw = row.get(colmap.get("debit", ""), "") if colmap.get("debit") else ""
                credit_raw = row.get(colmap.get("credit", ""), "") if colmap.get("credit") else ""
                debit_val = _clean_amount(debit_raw) if str(debit_raw).strip() else 0.0
                credit_val = _clean_amount(credit_raw) if str(credit_raw).strip() else 0.0
                if debit_val and credit_val:
                    raise ValueError("both debit and credit populated")
                signed_amount = -debit_val if debit_val else credit_val

            if signed_amount == 0:
                raise ValueError("zero amount")

            records.append({"datetime": date_val, "description": description, "amount": signed_amount})

        except Exception as e:
            skipped += 1
            skip_reasons.append(f"row {idx}: {e}")
            continue

    transactions_df = pd.DataFrame(records, columns=["datetime", "description", "amount"])
    if not transactions_df.empty:
        transactions_df = transactions_df.sort_values("datetime").reset_index(drop=True)

    return ParseResult(
        transactions=transactions_df,
        total_rows=len(raw_df),
        skipped_rows=skipped,
        skip_reasons=skip_reasons,
    )


def _clean_amount(value) -> float:
    """Strips currency symbols/commas/whitespace, returns a float."""
    if value is None:
        raise ValueError("missing amount")
    s = str(value).strip()
    if s == "":
        raise ValueError("empty amount")
    s = s.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "").strip()
    return float(s)