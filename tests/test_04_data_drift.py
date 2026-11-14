"""
Test Suite 04: Statistical Distribution & Data Drift Tests
Detects subtle population mean shifts using Z-score testing.
"""

from core.validator import DataValidator

def test_clean_data_splits_show_no_drift(clean_records):
    """Assertion: Random splits of the clean baseline should show no statistical drift."""
    half = len(clean_records) // 2
    split_a = clean_records[:half]
    split_b = clean_records[half:]
    
    result = DataValidator.assert_no_statistical_drift(split_a, split_b, "amount_mmk", max_z_score=3.0)
    assert result.passed, f"False positive drift alarm: {result.message}"

def test_corrupted_data_triggers_drift_alarm(clean_records, corrupted_records):
    """Assertion: An injected 50x spike in transaction amounts must trigger a drift alarm."""
    result = DataValidator.assert_no_statistical_drift(clean_records, corrupted_records, "amount_mmk", max_z_score=3.0)
    assert not result.passed, "Validator failed to detect massive statistical drift in transaction amounts!"
    assert "CRITICAL DATA DRIFT DETECTED" in result.message
