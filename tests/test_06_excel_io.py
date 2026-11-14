import os
import tempfile
import pytest
from core.excel_io import ExcelIO

def test_excel_write_and_read_roundtrip():
    clean_sample = [
        {"transaction_id": "TXN_001", "customer_id": "CUST_A", "amount_mmk": 250000.0, "township": "Hinthada"},
        {"transaction_id": "TXN_002", "customer_id": "CUST_B", "amount_mmk": 450000.0, "township": "Zalun"}
    ]
    quarantine_sample = [
        {"row_index": 3, "payload": {"transaction_id": "TXN_003", "age": -5}, "reasons": ["Invalid age -5"]}
    ]

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        wb = ExcelIO.create_audit_workbook(clean_sample, quarantine_sample)
        wb.save(tmp_path)
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 1000

        # Read back Clean_Data sheet
        read_rows = ExcelIO.read_excel(tmp_path)
        assert len(read_rows) >= 2
        # Verify first row
        assert read_rows[0]["transaction_id"] == "TXN_001"
        assert read_rows[0]["customer_id"] == "CUST_A"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_excel_export_bytes():
    clean_sample = [{"id": "1", "val": "100"}]
    quarantine_sample = [{"row_index": 2, "payload": {"id": "2"}, "reasons": ["Error"]}]
    raw_bytes = ExcelIO.export_excel_bytes(clean_sample, quarantine_sample)
    assert isinstance(raw_bytes, bytes)
    assert len(raw_bytes) > 2000 # Valid xlsx zip archive header
    assert raw_bytes[:4] == b"PK\x03\x04" # Standard zip/xlsx magic bytes
