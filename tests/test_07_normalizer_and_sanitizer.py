import pytest
from core.normalizer import DataNormalizer
from core.sanitizer import DataSanitizer

def test_myanmar_digits_normalization():
    assert DataNormalizer.normalize_myanmar_digits("၀၁၂၃၄၅၆၇၈၉") == "0123456789"
    assert DataNormalizer.normalize_myanmar_digits("ဖုန်း ၀၉၂၅၀၁၂၃၄၅၆") == "ဖုန်း 09250123456"

def test_phone_number_normalization():
    p1, ok1 = DataNormalizer.normalize_phone_number("09250123456")
    assert ok1 is True
    assert p1 == "+959250123456"

    p2, ok2 = DataNormalizer.normalize_phone_number("၀၉-၄၅၀၀-၁၂၃၄")
    assert ok2 is True
    assert p2 == "+95945001234"

    p3, ok3 = DataNormalizer.normalize_phone_number("95979111222")
    assert ok3 is True
    assert p3 == "+95979111222"

    p_bad, ok_bad = DataNormalizer.normalize_phone_number("12345")
    assert ok_bad is False

def test_date_normalization():
    d1, ok1 = DataNormalizer.normalize_date("25/12/2024")
    assert ok1 is True
    assert d1 == "2024-12-25"

    d2, ok2 = DataNormalizer.normalize_date("၂၀၂၄-၀၆-၁၅")
    assert ok2 is True
    assert d2 == "2024-06-15"

    d3, ok3 = DataNormalizer.normalize_date("01-05-2023 14:30:00")
    assert ok3 is True
    assert d3 == "2023-05-01"

def test_zawgyi_detection():
    # Regular Unicode string
    assert DataNormalizer.is_zawgyi("မင်္ဂလာပါ") is False
    # Zawgyi string with e vowel before consonant
    assert DataNormalizer.is_zawgyi("\u1031\u1000\u102c\u1004\u103a\u1038") is True

def test_sanitizer_auto_repairs_myanmar_digits_and_phones():
    dirty_rows = [
        {
            "transaction_id": "TXN_MYA_01",
            "customer_id": "CUST_99",
            "age": "၃၄",
            "amount_mmk": "၅၀၀,၀၀၀ MMK",
            "phone": "၀၉၂၅၀၁၂၃၄၅၆",
            "timestamp": "၁၅/၀၈/၂၀၂၄",
            "email": "khantsithu@example.com"
        },
        {
            "transaction_id": "TXN_BAD_02",
            "customer_id": "", # missing mandatory
            "age": "-5",
            "amount_mmk": "-100"
        }
    ]

    clean, quarantined = DataSanitizer.sanitize_dataset(dirty_rows, mask_pii=True)
    assert len(clean) == 1
    assert len(quarantined) == 1

    cleaned_row = clean[0]
    assert cleaned_row["age"] == 34
    assert cleaned_row["amount_mmk"] == 500000.0
    assert cleaned_row["timestamp"] == "2024-08-15"
    # PII masking verification: username masked, domain preserved
    assert cleaned_row["email"].startswith("kh***@")
    assert cleaned_row["email"].endswith("example.com")
    # Phone masked
    assert "****" in cleaned_row["phone"]
