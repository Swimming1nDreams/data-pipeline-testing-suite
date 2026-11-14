"""
Script to generate sample Excel workbook for DataSentinel QA testing.
"""
import os
import openpyxl
from core.excel_io import ExcelIO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

clean_rows = [
    {
        "transaction_id": "TXN_MM_1001",
        "customer_id": "CUST_YGN_01",
        "timestamp": "2024-05-10",
        "township": "Hinthada",
        "age": 29,
        "amount_mmk": 450000.0,
        "payment_type": "Mobile_Wallet",
        "email": "aungaung@mail.com",
        "phone": "+959250123456",
        "status": "COMPLETED"
    },
    {
        "transaction_id": "TXN_MM_1002",
        "customer_id": "CUST_YGN_02",
        "timestamp": "2024-05-11",
        "township": "Zalun",
        "age": 35,
        "amount_mmk": 820000.0,
        "payment_type": "Bank_Transfer",
        "email": "thida@mail.com",
        "phone": "+959450012345",
        "status": "RECONCILED"
    },
    {
        "transaction_id": "TXN_MM_1003",
        "customer_id": "CUST_YGN_03",
        "timestamp": "2024-05-12",
        "township": "Danubyu",
        "age": 42,
        "amount_mmk": 310000.0,
        "payment_type": "Cash_Agent",
        "email": "kyawkyaw@mail.com",
        "phone": "+959791112223",
        "status": "COMPLETED"
    }
]

quarantined = [
    {
        "row_index": 4,
        "payload": {"transaction_id": "TXN_MM_1004", "customer_id": "", "age": 14, "amount_mmk": -5000},
        "reasons": ["Null customer_id", "Age 14 < 18", "Negative amount"]
    }
]

wb = ExcelIO.create_audit_workbook(clean_rows, quarantined)
out_path = os.path.join(DATA_DIR, "sample_transactions.xlsx")
wb.save(out_path)
print(f"Created sample Excel workbook at {out_path} ({os.path.getsize(out_path)} bytes)")
