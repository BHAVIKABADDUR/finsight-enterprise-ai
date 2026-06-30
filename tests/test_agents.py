# tests/test_agents.py
# Unit tests for agent safety logic — SQL filter validation, HITL triggers
# Run with: pytest tests/test_agents.py -v

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.sql_agent import ALLOWED_COLUMNS, ALLOWED_OPERATORS
from hitl.interrupt_handler import should_trigger_hitl, HITL_THRESHOLD_AMOUNT


class TestSQLAgentSafety:
    """
    Tests for the SQL agent's security whitelist.
    These are critical — they prevent SQL injection or unauthorized
    data access even if the LLM is manipulated into generating
    malicious filter specifications.
    """

    def test_allowed_columns_does_not_include_id(self):
        # 'id' should not be directly filterable to prevent enumeration attacks
        assert "id" not in ALLOWED_COLUMNS

    def test_allowed_columns_includes_expected_fields(self):
        expected = {"amount", "category", "transaction_type", "is_flagged"}
        assert expected.issubset(ALLOWED_COLUMNS)

    def test_allowed_operators_are_safe_comparison_only(self):
        # No raw SQL execution operators should ever be allowed
        dangerous_operators = {"exec", "execute", "drop", "delete", "raw_sql"}
        assert dangerous_operators.isdisjoint(ALLOWED_OPERATORS)

    def test_allowed_operators_includes_expected_comparisons(self):
        expected = {"eq", "gt", "lt", "like"}
        assert expected.issubset(ALLOWED_OPERATORS)


class TestHITLTriggers:
    """
    Tests for the Human-in-the-Loop interrupt trigger logic.
    These rules determine when the agent graph must pause
    for human approval before continuing.
    """

    def test_high_risk_rating_triggers_hitl(self):
        decision = {"overall_risk_rating": "HIGH"}
        extracted_data = {"transactions": {"flagged_transactions": []}}

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is True
        assert "high" in reason.lower()

    def test_low_risk_rating_does_not_trigger_hitl(self):
        decision = {"overall_risk_rating": "LOW"}
        extracted_data = {"transactions": {"flagged_transactions": []}}

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is False

    def test_large_transaction_triggers_hitl(self):
        decision = {"overall_risk_rating": "LOW"}
        extracted_data = {
            "transactions": {
                "flagged_transactions": [
                    {"amount": HITL_THRESHOLD_AMOUNT + 1000}
                ]
            }
        }

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is True
        assert "large" in reason.lower()

    def test_transaction_below_threshold_does_not_trigger_alone(self):
        decision = {"overall_risk_rating": "LOW"}
        extracted_data = {
            "transactions": {
                "flagged_transactions": [
                    {"amount": HITL_THRESHOLD_AMOUNT - 1000}
                ]
            }
        }

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is False

    def test_multiple_flags_triggers_hitl(self):
        decision = {"overall_risk_rating": "LOW"}
        extracted_data = {
            "transactions": {
                "flagged_transactions": [
                    {"amount": 100}, {"amount": 200}, {"amount": 300}
                ]
            }
        }

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is True
        assert "multiple" in reason.lower()

    def test_two_flags_does_not_trigger_alone(self):
        decision = {"overall_risk_rating": "LOW"}
        extracted_data = {
            "transactions": {
                "flagged_transactions": [
                    {"amount": 100}, {"amount": 200}
                ]
            }
        }

        should_interrupt, reason = should_trigger_hitl(decision, extracted_data)

        assert should_interrupt is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])