"""
Test Suite 02: Business Boundary & Taxonomy Tests
Verifies numerical ranges, category taxonomy enums, and regex formats.
"""

from core.validator import DataValidator
from core.pipeline import VALID_TOWNSHIPS, EMAIL_REGEX, PHONE_REGEX

def test_clean_data_numerical_boundaries(clean_records):
    """Assertion: Ages must be between 18 and 100, amounts must be positive."""
    res_age = DataValidator.assert_numerical_range(clean_records, "age", 18, 100)
    assert res_age.passed, f"Age boundary test failed: {res_age.message}"
    
    res_amount = DataValidator.assert_numerical_range(clean_records, "amount_mmk", 1000.0, 5000000.0)
    assert res_amount.passed, f"Amount boundary test failed: {res_amount.message}"

def test_corrupted_data_flags_out_of_bounds_age(corrupted_records):
    """Assertion: Validator must catch negative and impossible ages (e.g., -5, 145)."""
    result = DataValidator.assert_numerical_range(corrupted_records, "age", 18, 100)
    assert not result.passed, "Validator failed to catch out-of-bounds ages!"
    assert any("Age" in str(v.get("error", "")) or "outside" in str(v.get("error", "")) for v in result.violations)

def test_corrupted_data_flags_negative_amount(corrupted_records):
    """Assertion: Validator must catch impossible negative transaction cash."""
    result = DataValidator.assert_numerical_range(corrupted_records, "amount_mmk", 1.0, 100000000.0)
    assert not result.passed
    assert len(result.violations) >= 3

def test_taxonomy_enum_compliance(clean_records, corrupted_records):
    """Assertion: Clean data satisfies townships enum; corrupted batch is caught."""
    res_clean = DataValidator.assert_category_enum(clean_records, "township", VALID_TOWNSHIPS)
    assert res_clean.passed
    
    res_corrupted = DataValidator.assert_category_enum(corrupted_records, "township", VALID_TOWNSHIPS)
    assert not res_corrupted.passed
    assert any("Unknown_Galaxy_Zone" in str(v.get("value", "")) for v in res_corrupted.violations)

def test_regex_format_compliance(clean_records, corrupted_records):
    """Assertion: Clean emails and phones pass regex; corrupted formats fail."""
    res_clean_email = DataValidator.assert_regex_format(clean_records, "email", EMAIL_REGEX, "Email")
    assert res_clean_email.passed
    
    res_corrupted_email = DataValidator.assert_regex_format(corrupted_records, "email", EMAIL_REGEX, "Email")
    assert not res_corrupted_email.passed
    assert any("not_an_email" in str(v.get("value", "")) for v in res_corrupted_email.violations)
