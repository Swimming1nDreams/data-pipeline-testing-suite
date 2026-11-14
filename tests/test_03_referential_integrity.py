"""
Test Suite 03: Primary Key & Referential Integrity Tests
Verifies unique key constraints and prevents duplicate row collisions.
"""

from core.validator import DataValidator

def test_clean_data_primary_key_uniqueness(clean_records):
    """Assertion: Baseline transactions must have 100% unique primary keys."""
    result = DataValidator.assert_unique_primary_key(clean_records, "transaction_id")
    assert result.passed, f"Duplicate transaction ID found in clean data: {result.message}"
    assert len(result.violations) == 0

def test_corrupted_data_catches_duplicate_primary_key(corrupted_records):
    """Assertion: Validator must catch duplicate primary key collisions in test batches."""
    result = DataValidator.assert_unique_primary_key(corrupted_records, "transaction_id")
    assert not result.passed, "Validator missed primary key duplicate collision!"
    assert len(result.violations) >= 1
    assert any("collision" in v.get("error", "") for v in result.violations)
