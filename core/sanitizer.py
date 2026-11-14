"""
DataSentinel QA - Automated Data Repair & Sanitization Engine
Performs rule-based data cleaning:
- Myanmar numerals (၀-၉ -> 0-9)
- Phone number normalization to E.164 (+959...)
- Date normalization to ISO-8601 (YYYY-MM-DD)
- Whitespace trimming and text spacing
- PII masking for compliant data sharing
- Dead-letter quarantine separation with granular diagnostic reasons
"""

import re
from typing import List, Dict, Tuple, Any
from core.normalizer import DataNormalizer

class DataSanitizer:
    @staticmethod
    def sanitize_dataset(rows: List[Dict[str, Any]], mask_pii: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Cleans and normalizes records with auto-repair capability.
        Returns: (clean_records, quarantined_records)
        """
        clean_records = []
        quarantined = []
        seen_keys = set()

        for idx, original_row in enumerate(rows):
            row = dict(original_row)
            errors = []
            applied_repairs = []

            # 1. Whitespace trimming and Myanmar numerals conversion across ALL string values
            for k, v in list(row.items()):
                if isinstance(v, str):
                    # Clean spacing
                    cleaned_val = DataNormalizer.normalize_text_spacing(v)
                    row[k] = cleaned_val

            # 2. Check Primary Key (transaction_id or first id column)
            pk_col = next((k for k in ["transaction_id", "id", "order_id", "record_id"] if k in row), None)
            if pk_col:
                pk_val = row.get(pk_col)
                if not pk_val or str(pk_val).strip() == "":
                    errors.append(f"Missing primary key [{pk_col}]")
                elif pk_val in seen_keys:
                    errors.append(f"Duplicate primary key collision: {pk_val}")
                else:
                    seen_keys.add(pk_val)

            # 3. Mandatory Customer / User ID Check
            id_col = next((k for k in ["customer_id", "user_id", "client_id"] if k in row), None)
            if id_col:
                if not row.get(id_col) or str(row.get(id_col)).strip() == "":
                    errors.append(f"Null or empty mandatory field [{id_col}]")

            # 4. Age Normalization & Boundaries
            if "age" in row and row["age"] != "":
                raw_age = DataNormalizer.normalize_myanmar_digits(str(row["age"]))
                try:
                    age = int(float(raw_age))
                    if age < 18 or age > 100:
                        errors.append(f"Invalid age: {age} outside [18, 100]")
                    else:
                        row["age"] = age
                except (ValueError, TypeError):
                    errors.append(f"Age '{row['age']}' is not a valid integer")

            # 5. Financial Amount Normalization & Boundaries
            amt_col = next((k for k in ["amount_mmk", "amount", "price", "total"] if k in row), None)
            if amt_col and row[amt_col] != "":
                raw_amt = DataNormalizer.normalize_myanmar_digits(str(row[amt_col]))
                # Remove currency symbols or commas
                raw_amt = re.sub(r"[,\s\$\£\€]|MMK|Ks", "", raw_amt, flags=re.IGNORECASE)
                try:
                    amt = float(raw_amt)
                    if amt <= 0:
                        errors.append(f"Non-positive cash amount: {amt}")
                    else:
                        row[amt_col] = amt
                except (ValueError, TypeError):
                    errors.append(f"Amount '{row[amt_col]}' is not a valid number")

            # 6. Phone Number Auto-Repair
            phone_col = next((k for k in ["phone", "mobile", "phone_number"] if k in row), None)
            if phone_col and row[phone_col] != "":
                norm_phone, is_valid_phone = DataNormalizer.normalize_phone_number(str(row[phone_col]))
                if is_valid_phone:
                    row[phone_col] = norm_phone
                else:
                    errors.append(f"Unrepairable phone number format: '{row[phone_col]}'")

            # 7. Date Auto-Repair to ISO YYYY-MM-DD
            date_col = next((k for k in ["timestamp", "date", "created_at", "trans_date"] if k in row), None)
            if date_col and row[date_col] != "":
                norm_date, is_valid_date = DataNormalizer.normalize_date(str(row[date_col]))
                if is_valid_date:
                    row[date_col] = norm_date
                # If date format is not recognized, but string exists, only error if strict date required

            # Route to Quarantine or Clean
            if errors:
                quarantined.append({
                    "row_index": idx + 1,
                    "payload": original_row,
                    "reasons": errors
                })
            else:
                # 8. PII Anonymization (Safe export)
                if mask_pii:
                    email_col = next((k for k in ["email", "user_email"] if k in row), None)
                    if email_col and "@" in str(row[email_col]):
                        parts = str(row[email_col]).split("@")
                        user_prefix = parts[0][:2] + "***" if len(parts[0]) >= 2 else "***"
                        domain = parts[1] if len(parts) > 1 else "masked.com"
                        row[email_col] = f"{user_prefix}@{domain}"

                    if phone_col and len(str(row[phone_col])) >= 8:
                        p = str(row[phone_col])
                        row[phone_col] = p[:4] + "****" + p[-3:]

                clean_records.append(row)

        return clean_records, quarantined
