"""
DataSentinel QA - Validation & Assertion Engine
Contains pure Python assertion and testing rules for data pipelines.
Zero heavy dependencies; extremely fast and accurate.
"""

import re
import math
from typing import List, Dict, Any, Tuple

class ValidationError(Exception):
    """Custom exception raised when a critical data assertion fails."""
    pass

class ValidationResult:
    """Encapsulates the outcome of a single validation test."""
    def __init__(self, test_name: str, passed: bool, message: str, violations: List[Dict] = None):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.violations = violations or []

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "message": self.message,
            "violation_count": len(self.violations),
            "sample_violations": self.violations[:5] # Top 5 for inspection
        }

class DataValidator:
    """Core test engine providing assertions for schemas, boundaries, and drift."""

    @staticmethod
    def assert_schema_contract(rows: List[Dict], expected_schema: Dict[str, type]) -> ValidationResult:
        """Verifies that all required columns exist and adhere to expected data types."""
        test_name = "test_schema_contract"
        if not rows:
            return ValidationResult(test_name, False, "Dataset is empty.")
            
        violations = []
        expected_keys = set(expected_schema.keys())
        
        for idx, row in enumerate(rows):
            row_keys = set(row.keys())
            missing = expected_keys - row_keys
            if missing:
                violations.append({"row": idx + 1, "error": f"Missing columns: {list(missing)}"})
                continue
                
            # Type Check
            for col, expected_type in expected_schema.items():
                val = row.get(col)
                if val is not None and val != "":
                    try:
                        expected_type(val)
                    except (ValueError, TypeError):
                        violations.append({
                            "row": idx + 1,
                            "column": col,
                            "value": val,
                            "error": f"Cannot cast to {expected_type.__name__}"
                        })
                        
        passed = len(violations) == 0
        msg = "All rows satisfy schema contract." if passed else f"Found {len(violations)} schema violations."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_no_nulls(rows: List[Dict], required_cols: List[str]) -> ValidationResult:
        """Asserts that mandatory primary/foreign key columns contain zero nulls or empty strings."""
        test_name = "test_no_nulls_integrity"
        violations = []
        
        for idx, row in enumerate(rows):
            for col in required_cols:
                val = row.get(col)
                if val is None or str(val).strip() == "":
                    violations.append({
                        "row": idx + 1,
                        "column": col,
                        "error": "Null or empty value in mandatory column"
                    })
                    
        passed = len(violations) == 0
        msg = f"Zero nulls in {required_cols}." if passed else f"Found {len(violations)} null violations in mandatory columns."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_unique_primary_key(rows: List[Dict], pk_column: str) -> ValidationResult:
        """Asserts that every record in the batch has a unique primary key."""
        test_name = "test_primary_key_uniqueness"
        seen = {}
        violations = []
        
        for idx, row in enumerate(rows):
            val = row.get(pk_column)
            if val in seen:
                violations.append({
                    "row": idx + 1,
                    "column": pk_column,
                    "value": val,
                    "error": f"Duplicate primary key collision (first seen at row {seen[val]})"
                })
            else:
                seen[val] = idx + 1
                
        passed = len(violations) == 0
        msg = f"Primary key '{pk_column}' is 100% unique." if passed else f"Found {len(violations)} duplicate primary key collisions."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_numerical_range(rows: List[Dict], column: str, min_val: float, max_val: float) -> ValidationResult:
        """Asserts that numerical values stay within realistic physiological/financial boundaries."""
        test_name = f"test_range_{column}"
        violations = []
        
        for idx, row in enumerate(rows):
            val = row.get(column)
            try:
                num = float(val)
                if num < min_val or num > max_val:
                    violations.append({
                        "row": idx + 1,
                        "column": column,
                        "value": num,
                        "error": f"Value {num} outside acceptable boundary [{min_val}, {max_val}]"
                    })
            except (ValueError, TypeError):
                violations.append({"row": idx + 1, "column": column, "value": val, "error": "Non-numeric value in range check"})
                
        passed = len(violations) == 0
        msg = f"All values in '{column}' within [{min_val}, {max_val}]." if passed else f"Found {len(violations)} boundary violations."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_category_enum(rows: List[Dict], column: str, allowed_categories: List[str]) -> ValidationResult:
        """Asserts that categorical variables strictly match standardized taxonomy."""
        test_name = f"test_enum_{column}"
        allowed_set = set(allowed_categories)
        violations = []
        
        for idx, row in enumerate(rows):
            val = str(row.get(column, "")).strip()
            if val not in allowed_set:
                violations.append({
                    "row": idx + 1,
                    "column": column,
                    "value": val,
                    "error": f"Unrecognized category '{val}'. Expected one of {allowed_categories}"
                })
                
        passed = len(violations) == 0
        msg = f"All values in '{column}' match valid taxonomy." if passed else f"Found {len(violations)} category enum violations."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_regex_format(rows: List[Dict], column: str, pattern: str, format_name: str) -> ValidationResult:
        """Asserts that string formats (Email, Phone, ISO dates) match expected regex patterns."""
        test_name = f"test_format_{column}"
        regex = re.compile(pattern)
        violations = []
        
        for idx, row in enumerate(rows):
            val = str(row.get(column, "")).strip()
            if not regex.match(val):
                violations.append({
                    "row": idx + 1,
                    "column": column,
                    "value": val,
                    "error": f"Failed {format_name} format pattern '{pattern}'"
                })
                
        passed = len(violations) == 0
        msg = f"All values in '{column}' conform to {format_name} format." if passed else f"Found {len(violations)} format violations."
        return ValidationResult(test_name, passed, msg, violations)

    @staticmethod
    def assert_no_statistical_drift(baseline_rows: List[Dict], test_rows: List[Dict], column: str, max_z_score=3.0) -> ValidationResult:
        """
        Detects data distribution drift by calculating Z-score difference in mean values.
        If test batch mean shifts beyond max_z_score * standard_error, test fails.
        """
        test_name = f"test_drift_{column}"
        
        def get_floats(rows):
            res = []
            for r in rows:
                try:
                    res.append(float(r[column]))
                except (ValueError, TypeError, KeyError):
                    pass
            return res
            
        base_vals = get_floats(baseline_rows)
        test_vals = get_floats(test_rows)
        
        if not base_vals or not test_vals:
            return ValidationResult(test_name, False, "Insufficient numerical data for drift calculation.")
            
        base_mean = sum(base_vals) / len(base_vals)
        base_variance = sum((x - base_mean) ** 2 for x in base_vals) / (len(base_vals) - 1 or 1)
        base_std = math.sqrt(base_variance)
        
        test_mean = sum(test_vals) / len(test_vals)
        
        # Standard error of the difference
        std_err = base_std / math.sqrt(len(test_vals)) if len(test_vals) > 0 else 1.0
        z_score = abs(test_mean - base_mean) / (std_err or 1.0)
        
        passed = z_score < max_z_score
        msg = (
            f"No drift detected. Baseline Mean: {base_mean:.2f}, Batch Mean: {test_mean:.2f}, "
            f"Z-Score: {z_score:.2f} (Threshold: {max_z_score:.2f})"
        ) if passed else (
            f"CRITICAL DATA DRIFT DETECTED! Z-Score: {z_score:.2f} exceeded threshold {max_z_score:.2f}. "
            f"Baseline Mean: {base_mean:.2f} vs Batch Mean: {test_mean:.2f}"
        )
        
        violations = []
        if not passed:
            violations.append({
                "metric": column,
                "baseline_mean": round(base_mean, 2),
                "batch_mean": round(test_mean, 2),
                "z_score": round(z_score, 2),
                "error": "Statistical distribution shift exceeds tolerance"
            })
            
        return ValidationResult(test_name, passed, msg, violations)
