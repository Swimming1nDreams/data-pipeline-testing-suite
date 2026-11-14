"""
Test Suite 01: Schema Contract & Null Integrity Tests
Verifies structural consistency, column datatypes, and mandatory fields.
"""

from core.validator import DataValidator
from core.pipeline import SCHEMA_CONTRACT

def test_clean_data_satisfies_schema_contract(clean_records):
    """Assertion: Clean baseline must satisfy 100% of schema contract rules."""
    result = DataValidator.assert_schema_contract(clean_records, SCHEMA_CONTRACT)
    assert result.passed, f"Clean data failed schema test: {result.message}"
    assert len(result.violations) == 0

def test_clean_data_has_zero_mandatory_nulls(clean_records):
    """Assertion: Primary keys and mandatory fields must have zero null values."""
    required = ["transaction_id", "customer_id", "timestamp", "township"]
    result = DataValidator.assert_no_nulls(clean_records, required)
    assert result.passed
    assert len(result.violations) == 0

def test_corrupted_data_correctly_flags_null_violations(corrupted_records):
    """Assertion: Validator must catch injected null customer_ids in corrupted test batch."""
    result = DataValidator.assert_no_nulls(corrupted_records, ["customer_id"])
    assert not result.passed, "Validator failed to catch injected null customer_ids!"
    assert len(result.violations) >= 5, f"Expected at least 5 null violations, found {len(result.violations)}"
