from app.parser import parse_csv


def test_parses_all_synthetic_csvs_with_zero_skipped(synthetic_csv_paths):
    for user_num, path in synthetic_csv_paths.items():
        with open(path) as f:
            result = parse_csv(f.read())
        assert result.skipped_rows == 0, f"user_{user_num}: expected 0 skipped rows, got {result.skipped_rows}"
        assert result.total_rows > 0
        assert not result.transactions.empty


def test_handles_split_debit_credit_columns():
    csv_content = (
        "Transaction Date,Narration,Debit,Credit\n"
        "2026-01-01,SALARY CREDIT,,75000.00\n"
        "2026-01-03,SWIGGY ORDER,450.50,\n"
    )
    result = parse_csv(csv_content)
    assert result.skipped_rows == 0
    assert len(result.transactions) == 2
    credit_row = result.transactions[result.transactions["amount"] > 0].iloc[0]
    debit_row = result.transactions[result.transactions["amount"] < 0].iloc[0]
    assert credit_row["amount"] == 75000.00
    assert debit_row["amount"] == -450.50


def test_skips_malformed_rows_without_crashing():
    csv_content = (
        "Date,Description,Amount,Type\n"
        "2026-01-01,VALID ROW,100,DEBIT\n"
        ",BROKEN NO DATE,100,DEBIT\n"
        "2026-01-02,,50,DEBIT\n"
        "2026-01-03,BAD AMOUNT,not_a_number,DEBIT\n"
        "2026-01-04,ZERO AMOUNT,0,DEBIT\n"
    )
    result = parse_csv(csv_content)
    assert len(result.transactions) == 1
    assert result.skipped_rows == 4


def test_strips_currency_symbols_and_commas():
    csv_content = 'Date,Description,Amount,Type\n2026-01-01,BIG PURCHASE,"\u20b91,234.56",DEBIT\n'
    result = parse_csv(csv_content)
    assert result.skipped_rows == 0
    assert result.transactions.iloc[0]["amount"] == -1234.56