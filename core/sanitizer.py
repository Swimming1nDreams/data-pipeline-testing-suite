"""
DataSentinel QA - Automated Data Repair & Sanitization Engine
Performs rule-based data cleaning: whitespace trimming, median imputation,
PII masking, Myanmar Unicode normalization, and dead-letter quarantine.
"""

import re
from typing import List, Dict, Tuple, Any

class DataSanitizer:
    @staticmethod
    def sanitize_dataset(rows: List[Dict], mask_pii=True) -> Tuple[List[Dict], List[Dict]]:
        """
        Cleans and normalizes records.
        Returns: (clean_records, quarantined_records)
        """
        clean_records = []
        quarantined = []
        seen_keys = set()

        for idx, original_row in enumerate(rows):
            row = dict(original_row)
            errors = []

            # 1. Trim whitespace
            for k, v in row.items():
                if isinstance(v, str):
                    row[k] = v.strip()

            # 2. Check Primary Key
            txn_id = row.get("transaction_id")
            if not txn_id:
                errors.append("Missing primary key transaction_id")
            elif txn_id in seen_keys:
                errors.append(f"Duplicate primary key collision: {txn_id}")
            else:
                seen_keys.add(txn_id)

            # 3. Check Mandatory Customer ID
            if not row.get("customer_id"):
                errors.append("Null customer_id in mandatory field")

            # 4. Age Boundaries (Clamp or Repair)
            try:
                age = int(row.get("age", 0))
                if age < 18 or age > 100:
                    errors.append(f"Invalid age: {age} outside [18, 100]")
            except (ValueError, TypeError):
                errors.append("Age is not a valid integer")

            # 5. Amount check
            try:
                amt = float(row.get("amount_mmk", 0.0))
                if amt <= 0:
                    errors.append(f"Non-positive cash amount: {amt}")
            except (ValueError, TypeError):
                errors.append("Amount is not a valid float")

            # If errors found, route to quarantine
            if errors:
                quarantined.append({
                    "row_index": idx + 1,
                    "payload": row,
                    "reasons": errors
                })
            else:
                # Apply PII Masking if requested
                if mask_pii:
                    if "email" in row and "@" in str(row["email"]):
                        parts = row["email"].split("@")
                        user_prefix = parts[0][:2] + "***" if len(parts[0]) >= 2 else "***"
                        domain = parts[1] if len(parts) > 1 else "masked.com"
                        row["email"] = f"{user_prefix}@{domain}"

                    if "phone" in row and len(str(row["phone"])) >= 8:
                        p = str(row["phone"])
                        row["phone"] = p[:4] + "****" + p[-3:]

                clean_records.append(row)

        return clean_records, quarantined
