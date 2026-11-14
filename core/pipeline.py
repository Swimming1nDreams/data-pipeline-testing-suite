"""
DataSentinel QA - ETL Execution Pipeline with Quarantine Mechanism
Processes raw CSV input, validates every record, commits clean records to SQLite,
and quarantines dirty records into a dead-letter audit log.
"""

import os
import csv
import sqlite3
from typing import Dict, List, Tuple, Any
from core.validator import DataValidator

SCHEMA_CONTRACT = {
    "transaction_id": str,
    "customer_id": str,
    "timestamp": str,
    "township": str,
    "age": int,
    "amount_mmk": float,
    "payment_type": str,
    "email": str,
    "phone": str,
    "status": str
}

VALID_TOWNSHIPS = ["Hinthada", "Zalun", "Danubyu", "Myanaung", "Kyangin", "Ingapu"]
VALID_PAYMENTS = ["Mobile_Wallet", "Bank_Transfer", "Cash_Agent", "Direct_Deposit"]
VALID_STATUSES = ["COMPLETED", "PENDING", "RECONCILED", "FLAGGED"]

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
PHONE_REGEX = r"^\+959\d{8,9}$"

class ETLPipeline:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "warehouse_pipeline.db")
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Clean production table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clean_transactions (
                transaction_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                timestamp TEXT,
                township TEXT,
                age INTEGER,
                amount_mmk REAL,
                payment_type TEXT,
                email TEXT,
                phone TEXT,
                status TEXT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Quarantine table for failed records (Dead-Letter Queue)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quarantine_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_payload TEXT,
                failed_field TEXT,
                error_reason TEXT,
                rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process_batch(self, csv_filepath: str) -> Dict[str, Any]:
        """Ingests a CSV file, runs row-level validation, and separates clean from quarantined data."""
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"Dataset not found at {csv_filepath}")

        rows = []
        with open(csv_filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        clean_records = []
        quarantined_records = []
        seen_txns = set()

        for idx, row in enumerate(rows):
            errors = []
            
            # Check 1: Mandatory Fields
            if not row.get("customer_id") or str(row.get("customer_id")).strip() == "":
                errors.append(("customer_id", "Null or empty customer_id"))
                
            # Check 2: Duplicate PK
            txn = row.get("transaction_id")
            if txn in seen_txns:
                errors.append(("transaction_id", f"Duplicate transaction_id: {txn}"))
            else:
                seen_txns.add(txn)
                
            # Check 3: Age bounds
            try:
                age = int(row.get("age", 0))
                if age < 18 or age > 100:
                    errors.append(("age", f"Age {age} outside allowable range [18, 100]"))
            except ValueError:
                errors.append(("age", "Invalid integer for age"))

            # Check 4: Amount bounds
            try:
                amount = float(row.get("amount_mmk", 0.0))
                if amount <= 0:
                    errors.append(("amount_mmk", f"Non-positive transaction amount: {amount}"))
            except ValueError:
                errors.append(("amount_mmk", "Invalid float for amount"))

            # Check 5: Township Enum
            if row.get("township") not in VALID_TOWNSHIPS:
                errors.append(("township", f"Unrecognized township: {row.get('township')}"))

            if errors:
                for field, reason in errors:
                    quarantined_records.append((str(row), field, reason))
            else:
                clean_records.append((
                    row["transaction_id"],
                    row["customer_id"],
                    row["timestamp"],
                    row["township"],
                    int(row["age"]),
                    float(row["amount_mmk"]),
                    row["payment_type"],
                    row["email"],
                    row["phone"],
                    row["status"]
                ))

        # Commit to DB
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Insert clean records
        cur.executemany("""
            INSERT OR REPLACE INTO clean_transactions 
            (transaction_id, customer_id, timestamp, township, age, amount_mmk, payment_type, email, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, clean_records)

        # Insert quarantined records
        cur.executemany("""
            INSERT INTO quarantine_audit (raw_payload, failed_field, error_reason)
            VALUES (?, ?, ?)
        """, quarantined_records)

        conn.commit()
        conn.close()

        return {
            "total_processed": len(rows),
            "clean_committed": len(clean_records),
            "quarantined_count": len(quarantined_records),
            "clean_ratio": round((len(clean_records) / (len(rows) or 1)) * 100, 2)
        }
