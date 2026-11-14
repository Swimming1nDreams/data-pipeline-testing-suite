"""
DataSentinel QA - Dynamic Data Contract Engine
Allows automatic schema contract inference from any arbitrary dataset (CSV/Excel),
custom rule declaration, JSON persistence, and dynamic assertion evaluation.
Inspired by Great Expectations & Soda Core, but zero dependency.
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.validator import ValidationResult
from core.normalizer import DataNormalizer

class DataContract:
    @staticmethod
    def infer_contract(rows: List[Dict[str, Any]], dataset_name: str = "Dataset") -> Dict[str, Any]:
        """
        Analyzes a sample or full dataset to infer production-grade data quality contracts:
        - Data types (integer, float, date, phone, email, string)
        - Nullability constraints
        - Uniqueness / Primary Key candidates
        - Min / Max numerical boundaries
        - Categorical enum taxonomy (if cardinality <= 15)
        """
        if not rows:
            return {"dataset": dataset_name, "columns": {}, "primary_key": None}

        total = len(rows)
        headers = list(rows[0].keys())
        columns_spec = {}
        primary_key_candidate = None

        for col in headers:
            raw_vals = [r.get(col, "") for r in rows]
            non_empty_vals = [v for v in raw_vals if v is not None and str(v).strip() != ""]
            null_count = total - len(non_empty_vals)
            distinct_vals = set(non_empty_vals)

            # Uniqueness
            is_unique = (len(distinct_vals) == total) and total > 0
            if is_unique and not primary_key_candidate and ("id" in col.lower() or "code" in col.lower() or "key" in col.lower()):
                primary_key_candidate = col

            # Type Inference
            col_type = "string"
            min_num = None
            max_num = None
            enum_values = None
            format_rule = None

            # Test integer
            all_int = True
            all_float = True
            all_date = True
            all_phone = True
            all_email = True

            int_vals = []
            float_vals = []

            for val in non_empty_vals:
                s_val = DataNormalizer.normalize_myanmar_digits(str(val).strip())
                # Integer test
                if all_int:
                    try:
                        int_vals.append(int(s_val))
                    except ValueError:
                        all_int = False

                # Float test
                if all_float:
                    try:
                        float_vals.append(float(s_val))
                    except ValueError:
                        all_float = False

                # Phone test
                if all_phone:
                    norm_p, p_valid = DataNormalizer.normalize_phone_number(s_val)
                    if not p_valid:
                        all_phone = False

                # Date test
                if all_date:
                    norm_d, d_valid = DataNormalizer.normalize_date(s_val)
                    if not d_valid:
                        all_date = False

                # Email test
                if all_email:
                    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", s_val):
                        all_email = False

            if non_empty_vals:
                if all_phone and len(non_empty_vals) > 0:
                    col_type = "phone"
                    format_rule = "E.164"
                elif all_date and len(non_empty_vals) > 0:
                    col_type = "date"
                    format_rule = "ISO-8601"
                elif all_email and len(non_empty_vals) > 0:
                    col_type = "email"
                    format_rule = "RFC-5322"
                elif all_int and len(int_vals) > 0:
                    col_type = "integer"
                    min_num = min(int_vals)
                    max_num = max(int_vals)
                elif all_float and len(float_vals) > 0:
                    col_type = "float"
                    min_num = min(float_vals)
                    max_num = max(float_vals)
                elif len(distinct_vals) <= 15:
                    col_type = "enum"
                    enum_values = sorted(list(distinct_vals))

            columns_spec[col] = {
                "type": col_type,
                "nullable": (null_count > 0),
                "null_count": null_count,
                "distinct_count": len(distinct_vals),
                "is_unique": is_unique,
                "min": min_num,
                "max": max_num,
                "allowed_values": enum_values,
                "format": format_rule
            }

        return {
            "dataset": dataset_name,
            "version": "1.0",
            "inferred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows_sampled": total,
            "primary_key": primary_key_candidate or (headers[0] if headers else None),
            "columns": columns_spec
        }

    @staticmethod
    def validate(rows: List[Dict[str, Any]], contract: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validates arbitrary rows against a contract dictionary.
        Returns a list of ValidationResults.
        """
        results = []
        cols_spec = contract.get("columns", {})
        pk_col = contract.get("primary_key")

        # 1. Primary Key Uniqueness Test
        if pk_col and pk_col in cols_spec:
            seen_pk = {}
            pk_violations = []
            for idx, r in enumerate(rows):
                val = r.get(pk_col)
                if val is None or str(val).strip() == "":
                    pk_violations.append({"row": idx + 1, "column": pk_col, "error": "Primary key cannot be empty or null"})
                elif val in seen_pk:
                    pk_violations.append({"row": idx + 1, "column": pk_col, "value": val, "error": f"Duplicate PK collision with row {seen_pk[val]}"})
                else:
                    seen_pk[val] = idx + 1
            passed = (len(pk_violations) == 0)
            results.append(ValidationResult(
                f"Primary Key Uniqueness [{pk_col}]",
                passed,
                f"Primary key '{pk_col}' unique." if passed else f"Found {len(pk_violations)} primary key collisions.",
                pk_violations
            ))

        # 2. Column constraints
        for col, spec in cols_spec.items():
            c_type = spec.get("type", "string")
            is_nullable = spec.get("nullable", True)
            min_v = spec.get("min")
            max_v = spec.get("max")
            allowed = spec.get("allowed_values")
            fmt = spec.get("format")

            null_violations = []
            type_violations = []
            range_violations = []
            enum_violations = []
            format_violations = []

            for idx, r in enumerate(rows):
                val = r.get(col)
                is_empty = (val is None or str(val).strip() == "")

                # Null check
                if not is_nullable and is_empty:
                    null_violations.append({"row": idx + 1, "column": col, "error": f"Non-nullable column '{col}' has empty value"})
                    continue

                if is_empty:
                    continue

                s_val = DataNormalizer.normalize_myanmar_digits(str(val).strip())

                # Type & Range Checks
                if c_type == "integer":
                    try:
                        iv = int(s_val)
                        if min_v is not None and iv < min_v:
                            range_violations.append({"row": idx + 1, "column": col, "value": iv, "error": f"Value {iv} < min allowed {min_v}"})
                        if max_v is not None and iv > max_v:
                            range_violations.append({"row": idx + 1, "column": col, "value": iv, "error": f"Value {iv} > max allowed {max_v}"})
                    except ValueError:
                        type_violations.append({"row": idx + 1, "column": col, "value": val, "error": "Cannot cast to integer"})

                elif c_type == "float":
                    try:
                        fv = float(s_val)
                        if min_v is not None and fv < min_v:
                            range_violations.append({"row": idx + 1, "column": col, "value": fv, "error": f"Value {fv} < min allowed {min_v}"})
                        if max_v is not None and fv > max_v:
                            range_violations.append({"row": idx + 1, "column": col, "value": fv, "error": f"Value {fv} > max allowed {max_v}"})
                    except ValueError:
                        type_violations.append({"row": idx + 1, "column": col, "value": val, "error": "Cannot cast to float"})

                elif c_type == "phone":
                    norm_p, p_valid = DataNormalizer.normalize_phone_number(s_val)
                    if not p_valid:
                        format_violations.append({"row": idx + 1, "column": col, "value": val, "error": "Invalid Myanmar/E.164 phone format"})

                elif c_type == "date":
                    norm_d, d_valid = DataNormalizer.normalize_date(s_val)
                    if not d_valid:
                        format_violations.append({"row": idx + 1, "column": col, "value": val, "error": "Invalid date format"})

                elif c_type == "email":
                    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", s_val):
                        format_violations.append({"row": idx + 1, "column": col, "value": val, "error": "Invalid email format"})

                if allowed and s_val not in allowed:
                    enum_violations.append({"row": idx + 1, "column": col, "value": s_val, "error": f"Value '{s_val}' not in allowed taxonomy {allowed}"})

            # Append results for this column
            if not is_nullable:
                results.append(ValidationResult(
                    f"Mandatory Column [{col}]",
                    len(null_violations) == 0,
                    f"Column '{col}' has zero empty values." if len(null_violations) == 0 else f"Found {len(null_violations)} null violations.",
                    null_violations
                ))
            if type_violations:
                results.append(ValidationResult(
                    f"Type Adherence [{col} -> {c_type}]",
                    False,
                    f"Found {len(type_violations)} type conversion errors in '{col}'.",
                    type_violations
                ))
            if range_violations:
                results.append(ValidationResult(
                    f"Boundary Range [{col}]",
                    False,
                    f"Found {len(range_violations)} out-of-boundary values in '{col}'.",
                    range_violations
                ))
            if enum_violations:
                results.append(ValidationResult(
                    f"Taxonomy Enum [{col}]",
                    False,
                    f"Found {len(enum_violations)} taxonomy violations in '{col}'.",
                    enum_violations
                ))
            if format_violations:
                results.append(ValidationResult(
                    f"Format Pattern [{col} -> {fmt or c_type}]",
                    False,
                    f"Found {len(format_violations)} pattern formatting violations in '{col}'.",
                    format_violations
                ))

        return results
