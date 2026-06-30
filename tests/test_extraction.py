# tests/test_extraction.py
# Unit tests for the Silver layer data cleaning functions
# Run with: pytest tests/test_extraction.py -v

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pipeline.silver import (
    clean_amount,
    clean_date,
    clean_text,
    clean_transaction_type,
    detect_anomalies
)


class TestCleanAmount:
    """Tests for the amount cleaning function — must handle messy real-world input."""

    def test_clean_numeric_input(self):
        assert clean_amount(1234.56) == 1234.56

    def test_clean_string_with_commas(self):
        assert clean_amount("1,234.56") == 1234.56

    def test_clean_string_with_currency_symbol(self):
        assert clean_amount("AED 1234.56") == 1234.56

    def test_clean_string_with_dollar_sign(self):
        assert clean_amount("$1,234.56") == 1234.56

    def test_clean_empty_string_defaults_to_zero(self):
        assert clean_amount("") == 0.0

    def test_clean_invalid_string_defaults_to_zero(self):
        assert clean_amount("not a number") == 0.0

    def test_clean_integer_input(self):
        assert clean_amount(500) == 500.0


class TestCleanDate:
    """Tests for date standardization across multiple input formats."""

    def test_iso_format_passes_through(self):
        assert clean_date("2026-06-15") == "2026-06-15"

    def test_dd_mm_yyyy_format(self):
        assert clean_date("15/06/2026") == "2026-06-15"

    def test_dd_mon_yyyy_format(self):
        assert clean_date("15 Jun 2026") == "2026-06-15"

    def test_empty_date_defaults_to_today(self):
        result = clean_date("")
        # Should return today's date in YYYY-MM-DD format, not crash
        assert len(result) == 10
        assert result.count("-") == 2


class TestCleanText:
    """Tests for text field cleaning — whitespace and formatting."""

    def test_strips_leading_trailing_whitespace(self):
        assert clean_text("  Emirates NBD  ") == "Emirates NBD"

    def test_collapses_multiple_spaces(self):
        assert clean_text("Emirates    NBD   Bank") == "Emirates NBD Bank"

    def test_empty_input_returns_empty_string(self):
        assert clean_text("") == ""

    def test_none_input_returns_empty_string(self):
        assert clean_text(None) == ""


class TestCleanTransactionType:
    """Tests for transaction type normalization."""

    def test_credit_variants(self):
        assert clean_transaction_type("credit") == "credit"
        assert clean_transaction_type("CR") == "credit"
        assert clean_transaction_type("deposit") == "credit"

    def test_debit_variants(self):
        assert clean_transaction_type("debit") == "debit"
        assert clean_transaction_type("DR") == "debit"
        assert clean_transaction_type("withdrawal") == "debit"

    def test_unknown_defaults_to_debit(self):
        assert clean_transaction_type("xyz") == "debit"

    def test_empty_defaults_to_debit(self):
        assert clean_transaction_type("") == "debit"


class TestAnomalyDetection:
    """Tests for the rule-based anomaly detection engine."""

    def test_large_amount_is_flagged(self):
        txn = {"amount": 100000, "description": "Test Vendor"}
        is_flagged, reason = detect_anomalies(txn, [txn])
        assert is_flagged is True
        assert "large" in reason.lower()

    def test_normal_amount_not_flagged(self):
        txn = {"amount": 5000, "description": "Normal Payment"}
        is_flagged, reason = detect_anomalies(txn, [txn])
        assert is_flagged is False

    def test_suspicious_round_number_is_flagged(self):
        txn = {"amount": 50000, "description": "Cash Withdrawal"}
        is_flagged, reason = detect_anomalies(txn, [txn])
        assert is_flagged is True
        assert "round" in reason.lower()

    def test_duplicate_transaction_is_flagged(self):
        txn1 = {"amount": 5000, "description": "Spinneys Dubai"}
        txn2 = {"amount": 5000, "description": "Spinneys Dubai"}
        is_flagged, reason = detect_anomalies(txn1, [txn1, txn2])
        assert is_flagged is True
        assert "duplicate" in reason.lower()

    def test_unknown_vendor_is_flagged(self):
        txn = {"amount": 5000, "description": "UNKNOWN VENDOR TRANSFER"}
        is_flagged, reason = detect_anomalies(txn, [txn])
        assert is_flagged is True
        assert "unknown" in reason.lower()

    def test_zero_amount_is_flagged(self):
        txn = {"amount": 0, "description": "Test"}
        is_flagged, reason = detect_anomalies(txn, [txn])
        assert is_flagged is True
        assert "invalid" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])