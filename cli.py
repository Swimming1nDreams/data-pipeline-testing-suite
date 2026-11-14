"""
DataSentinel QA - Command-Line Interface (CLI)
Provides convenient commands to run the test suite, audit files, and generate synthetic data.
"""

import sys
import os
import subprocess
import argparse
import json
import csv
from core.validator import DataValidator
from core.pipeline import SCHEMA_CONTRACT, VALID_TOWNSHIPS, EMAIL_REGEX, PHONE_REGEX
from core.synthetic_generator import generate_clean_baseline, generate_corrupted_batch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")

def cmd_run_tests(args):
    """Executes pytest suite and generates a structured summary."""
    print("=" * 70)
    print("  DataSentinel QA - Running Automated Test Suite (Pytest)")
    print("=" * 70)
    
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--cov=core"]
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
        
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(REPORTS_DIR, "latest_cli_run.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(result.stdout)
        
    print(f"\n[CLI] Detailed test logs saved to: {report_file}")
    print("=" * 70)
    return result.returncode

def cmd_audit_file(args):
    """Performs deep validation on an input CSV and prints diagnostics."""
    filepath = args.filepath
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return 1

    print("=" * 70)
    print(f"  DataSentinel QA - Auditing File: {os.path.basename(filepath)}")
    print("=" * 70)

    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print(f"Total Rows Loaded: {len(rows)}")
    print("-" * 70)

    tests = [
        ("Schema Contract", lambda: DataValidator.assert_schema_contract(rows, SCHEMA_CONTRACT)),
        ("Mandatory Nulls", lambda: DataValidator.assert_no_nulls(rows, ["transaction_id", "customer_id"])),
        ("Primary Key Uniqueness", lambda: DataValidator.assert_unique_primary_key(rows, "transaction_id")),
        ("Age Range [18, 100]", lambda: DataValidator.assert_numerical_range(rows, "age", 18, 100)),
        ("Positive Cash Amount", lambda: DataValidator.assert_numerical_range(rows, "amount_mmk", 1.0, 100000000.0)),
        ("Township Taxonomy Enum", lambda: DataValidator.assert_category_enum(rows, "township", VALID_TOWNSHIPS)),
        ("Email Regex Format", lambda: DataValidator.assert_regex_format(rows, "email", EMAIL_REGEX, "Email")),
        ("Phone Regex Format", lambda: DataValidator.assert_regex_format(rows, "phone", PHONE_REGEX, "Phone"))
    ]

    summary = []
    for test_name, test_fn in tests:
        res = test_fn()
        status_badge = "[ PASS ]" if res.passed else "[ FAIL ]"
        print(f"{status_badge} {test_name:<26} : {res.message}")
        summary.append(res.to_dict())

    # Save JSON report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_json = os.path.join(REPORTS_DIR, f"audit_{os.path.basename(filepath)}.json")
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("-" * 70)
    print(f"[CLI] Audit JSON saved to: {report_json}\n")

def cmd_generate_data(args):
    """Generates clean and corrupted test data."""
    print("Generating synthetic datasets...")
    generate_clean_baseline(count=args.clean_count)
    generate_corrupted_batch(count=args.corrupt_count)
    print("Data generation complete.")

def main():
    parser = argparse.ArgumentParser(description="DataSentinel QA - Automated Pipeline Testing Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-tests
    p_test = subparsers.add_parser("run-tests", help="Run full automated pytest suite")
    p_test.set_defaults(func=cmd_run_tests)

    # audit-file
    p_audit = subparsers.add_parser("audit", help="Audit a specific CSV file against data assertions")
    p_audit.add_argument("filepath", type=str, help="Path to CSV file to audit")
    p_audit.set_defaults(func=cmd_audit_file)

    # generate-data
    p_gen = subparsers.add_parser("generate-data", help="Generate synthetic clean and corrupted test datasets")
    p_gen.add_argument("--clean-count", type=int, default=1000, help="Number of clean records (default 1000)")
    p_gen.add_argument("--corrupt-count", type=int, default=300, help="Number of corrupted records (default 300)")
    p_gen.set_defaults(func=cmd_generate_data)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
