"""
DataSentinel QA - Advanced Web Server & REST API Engine
Supports Data Profiling, Custom Rule Engineering, SQL Sandbox,
Auto-Sanitization, Dynamic Contracts, Excel (.xlsx) Export & Ingestion, and Pytest execution.
"""

import os
import sys
import json
import csv
import time
import base64
import sqlite3
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
RULES_FILE = os.path.join(DATA_DIR, "custom_rules.json")

from core.validator import DataValidator
from core.pipeline import ETLPipeline, SCHEMA_CONTRACT, VALID_TOWNSHIPS, EMAIL_REGEX, PHONE_REGEX
from core.profiler import DataProfiler
from core.sanitizer import DataSanitizer
from core.sql_sandbox import SQLSandbox
from core.excel_io import ExcelIO
from core.contract import DataContract
from core.normalizer import DataNormalizer

class DataSentinelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/run-pytest":
            self.handle_run_pytest()
        elif path == "/api/audit":
            self.handle_audit(query)
        elif path == "/api/profile":
            self.handle_profile(query)
        elif path == "/api/sanitize":
            self.handle_sanitize(query)
        elif path == "/api/custom-rules":
            self.handle_get_rules()
        elif path == "/api/etl":
            self.handle_etl(query)
        elif path == "/api/quarantine-records":
            self.handle_quarantine_records()
        elif path == "/api/distribution-data":
            self.handle_distribution_data()
        elif path == "/api/infer-contract":
            self.handle_infer_contract(query)
        elif path == "/api/export-excel":
            self.handle_export_excel(query)
        elif path == "/api/list-files":
            self.handle_list_files()
        elif path == "/" or path == "/index.html":
            self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload-audit":
            self.handle_upload_audit()
        elif parsed.path == "/api/upload-binary":
            self.handle_upload_binary()
        elif parsed.path == "/api/query-sql":
            self.handle_sql_query()
        elif parsed.path == "/api/custom-rules":
            self.handle_save_rule()
        elif parsed.path == "/api/validate-contract":
            self.handle_validate_contract()
        else:
            self.send_response(404)
            self.end_headers()

    def _get_dataset_rows(self, filename):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            return []
        if filename.lower().endswith(".xlsx"):
            return ExcelIO.read_excel(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def handle_list_files(self):
        files = []
        if os.path.exists(DATA_DIR):
            for f in os.listdir(DATA_DIR):
                if f.endswith((".csv", ".xlsx")) and not f.startswith("."):
                    size_kb = round(os.path.getsize(os.path.join(DATA_DIR, f)) / 1024, 1)
                    files.append({"name": f, "size_kb": size_kb})
        self.send_json_response({"files": files})

    def handle_run_pytest(self):
        t0 = time.time()
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--cov=core"]
        res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        duration = round(time.time() - t0, 2)

        data = {
            "output": res.stdout or res.stderr,
            "returncode": res.returncode,
            "duration": f"{duration}s",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.send_json_response(data)

    def handle_audit(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        rows = self._get_dataset_rows(filename)

        if not rows:
            self.send_json_response({"error": f"File {filename} not found or empty"}, 404)
            return

        base_rows = self._get_dataset_rows("baseline_clean.csv")

        tests = [
            ("Schema Contract Verification", lambda: DataValidator.assert_schema_contract(rows, SCHEMA_CONTRACT)),
            ("Mandatory Null Integrity Check", lambda: DataValidator.assert_no_nulls(rows, ["transaction_id", "customer_id"])),
            ("Primary Key Uniqueness Test", lambda: DataValidator.assert_unique_primary_key(rows, "transaction_id")),
            ("Age Range Assertion [18, 100]", lambda: DataValidator.assert_numerical_range(rows, "age", 18, 100)),
            ("Positive Amount Assertion", lambda: DataValidator.assert_numerical_range(rows, "amount_mmk", 1.0, 100000000.0)),
            ("Township Taxonomy Enum Check", lambda: DataValidator.assert_category_enum(rows, "township", VALID_TOWNSHIPS)),
            ("Email Regex Pattern Format", lambda: DataValidator.assert_regex_format(rows, "email", EMAIL_REGEX, "Email")),
            ("Phone Regex Pattern Format", lambda: DataValidator.assert_regex_format(rows, "phone", PHONE_REGEX, "Phone")),
            ("Statistical Data Drift Test (MMK)", lambda: DataValidator.assert_no_statistical_drift(base_rows, rows, "amount_mmk", max_z_score=3.0))
        ]

        # Apply any custom user-configured rules
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as rf:
                    custom_rules = json.load(rf)
                for cr in custom_rules:
                    rule_type = cr.get("type")
                    col = cr.get("column")
                    if rule_type == "range":
                        min_v, max_v = float(cr["min"]), float(cr["max"])
                        tests.append((f"Custom Range [{col} in {min_v}-{max_v}]", lambda c=col, mn=min_v, mx=max_v: DataValidator.assert_numerical_range(rows, c, mn, mx)))
                    elif rule_type == "not_null":
                        tests.append((f"Custom Not-Null [{col}]", lambda c=col: DataValidator.assert_no_nulls(rows, [c])))
                    elif rule_type == "enum":
                        allowed = [x.strip() for x in cr["values"].split(",")]
                        tests.append((f"Custom Enum [{col}]", lambda c=col, a=allowed: DataValidator.assert_category_enum(rows, c, a)))
            except Exception:
                pass

        results = []
        for name, fn in tests:
            r = fn()
            results.append({
                "test_name": name,
                "passed": r.passed,
                "message": r.message,
                "violations_count": len(r.violations),
                "sample_violations": r.violations[:8]
            })

        self.send_json_response({
            "filename": filename,
            "total_rows": len(rows),
            "results": results,
            "passed_count": sum(1 for r in results if r["passed"]),
            "failed_count": sum(1 for r in results if not r["passed"]),
            "audited_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def handle_profile(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        rows = self._get_dataset_rows(filename)
        profile = DataProfiler.profile_dataset(rows)
        profile["filename"] = filename
        self.send_json_response(profile)

    def handle_sanitize(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        rows = self._get_dataset_rows(filename)
        clean_rows, quarantined = DataSanitizer.sanitize_dataset(rows, mask_pii=True)
        
        # Save cleaned file for user download
        clean_filename = f"repaired_{os.path.splitext(filename)[0]}.csv"
        clean_path = os.path.join(DATA_DIR, clean_filename)
        if clean_rows:
            with open(clean_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(clean_rows[0].keys()))
                writer.writeheader()
                writer.writerows(clean_rows)

        self.send_json_response({
            "original_count": len(rows),
            "clean_count": len(clean_rows),
            "quarantined_count": len(quarantined),
            "cleaned_file": clean_filename,
            "sample_cleaned": clean_rows[:5],
            "sample_quarantined": quarantined[:5]
        })

    def handle_infer_contract(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        rows = self._get_dataset_rows(filename)
        contract = DataContract.infer_contract(rows, dataset_name=filename)
        self.send_json_response(contract)

    def handle_validate_contract(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        filename = body.get("filename", "incoming_corrupted_batch.csv")
        contract = body.get("contract")

        rows = self._get_dataset_rows(filename)
        if not rows:
            self.send_json_response({"error": "File not found or empty"}, 404)
            return

        results = DataContract.validate(rows, contract)
        formatted = [r.to_dict() for r in results]

        self.send_json_response({
            "filename": filename,
            "total_rows": len(rows),
            "results": formatted,
            "passed_count": sum(1 for r in formatted if r["passed"]),
            "failed_count": sum(1 for r in formatted if not r["passed"]),
            "validated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def handle_export_excel(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        rows = self._get_dataset_rows(filename)
        if not rows:
            self.send_response(404)
            self.end_headers()
            return

        clean_rows, quarantined = DataSanitizer.sanitize_dataset(rows, mask_pii=False)
        xlsx_bytes = ExcelIO.export_excel_bytes(clean_rows, quarantined)

        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="DataSentinel_Audit_{os.path.splitext(filename)[0]}.xlsx"')
        self.send_header("Content-Length", str(len(xlsx_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(xlsx_bytes)

    def handle_sql_query(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        filename = body.get("filename", "incoming_corrupted_batch.csv")
        query = body.get("query", "SELECT * FROM transactions LIMIT 10")
        
        rows = self._get_dataset_rows(filename)
        res = SQLSandbox.execute_query(rows, query)
        self.send_json_response(res)

    def handle_get_rules(self):
        if not os.path.exists(RULES_FILE):
            self.send_json_response([])
            return
        with open(RULES_FILE, "r", encoding="utf-8") as rf:
            self.send_json_response(json.load(rf))

    def handle_save_rule(self):
        length = int(self.headers.get("Content-Length", 0))
        rule = json.loads(self.rfile.read(length).decode("utf-8"))
        
        rules = []
        if os.path.exists(RULES_FILE):
            with open(RULES_FILE, "r", encoding="utf-8") as f:
                rules = json.load(f)
        rules.append(rule)
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)
            
        self.send_json_response({"status": "saved", "rules": rules})

    def handle_etl(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            self.send_json_response({"error": "File not found"}, 404)
            return

        pipeline = ETLPipeline()
        report = pipeline.process_batch(filepath)
        self.send_json_response(report)

    def handle_quarantine_records(self):
        db_path = os.path.join(DATA_DIR, "warehouse_pipeline.db")
        if not os.path.exists(db_path):
            self.send_json_response({"records": []})
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, raw_payload, failed_field, error_reason, rejected_at
            FROM quarantine_audit
            ORDER BY id DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        conn.close()

        records = []
        for r in rows:
            records.append({
                "id": r[0],
                "payload": r[1],
                "field": r[2],
                "reason": r[3],
                "rejected_at": r[4]
            })
        self.send_json_response({"records": records, "total": len(records)})

    def handle_distribution_data(self):
        base_rows = self._get_dataset_rows("baseline_clean.csv")
        batch_rows = self._get_dataset_rows("incoming_corrupted_batch.csv")

        def get_amounts(rows):
            res = []
            for r in rows:
                try:
                    val = float(DataNormalizer.normalize_myanmar_digits(str(r.get("amount_mmk", ""))))
                    res.append(val)
                except:
                    pass
            return res

        base_amt = get_amounts(base_rows)
        batch_amt = get_amounts(batch_rows)

        bins = ["< 100K", "100K-300K", "300K-500K", "500K-750K", "750K-1M", "> 1M (Outlier)"]
        
        def bin_counts(amounts):
            c = [0, 0, 0, 0, 0, 0]
            for a in amounts:
                if a < 100000: c[0] += 1
                elif a < 300000: c[1] += 1
                elif a < 500000: c[2] += 1
                elif a < 750000: c[3] += 1
                elif a <= 1000000: c[4] += 1
                else: c[5] += 1
            return c

        base_counts = bin_counts(base_amt)
        batch_counts = bin_counts(batch_amt)
        base_mean = round(sum(base_amt) / (len(base_amt) or 1), 2)
        batch_mean = round(sum(batch_amt) / (len(batch_amt) or 1), 2)

        self.send_json_response({
            "bins": bins,
            "baseline": base_counts,
            "batch": batch_counts,
            "baseline_mean": base_mean,
            "batch_mean": batch_mean,
            "base_total": len(base_amt),
            "batch_total": len(batch_amt)
        })

    def handle_upload_binary(self):
        """Accepts base64 encoded CSV or XLSX file and writes to data/."""
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        filename = body.get("filename", "uploaded_data.csv")
        b64data = body.get("base64", "")

        file_bytes = base64.b64decode(b64data)
        safe_path = os.path.join(DATA_DIR, os.path.basename(filename))
        with open(safe_path, "wb") as f:
            f.write(file_bytes)

        # Profile and return rows
        rows = self._get_dataset_rows(os.path.basename(filename))
        self.send_json_response({
            "status": "success",
            "filename": os.path.basename(filename),
            "total_rows": len(rows),
            "message": f"Successfully loaded {len(rows)} records into QA engine."
        })

    def handle_upload_audit(self):
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length).decode("utf-8")
        
        lines = [l for l in post_data.splitlines() if l.strip()]
        if len(lines) < 2:
            self.send_json_response({"error": "CSV requires header and at least one data row"}, 400)
            return

        reader = csv.DictReader(lines)
        rows = list(reader)

        base_rows = self._get_dataset_rows("baseline_clean.csv")

        tests = [
            ("Schema Contract Verification", lambda: DataValidator.assert_schema_contract(rows, SCHEMA_CONTRACT)),
            ("Mandatory Null Integrity Check", lambda: DataValidator.assert_no_nulls(rows, ["transaction_id", "customer_id"])),
            ("Primary Key Uniqueness Test", lambda: DataValidator.assert_unique_primary_key(rows, "transaction_id")),
            ("Age Range Assertion [18, 100]", lambda: DataValidator.assert_numerical_range(rows, "age", 18, 100)),
            ("Positive Amount Assertion", lambda: DataValidator.assert_numerical_range(rows, "amount_mmk", 1.0, 100000000.0)),
            ("Township Taxonomy Enum Check", lambda: DataValidator.assert_category_enum(rows, "township", VALID_TOWNSHIPS)),
            ("Email Regex Pattern Format", lambda: DataValidator.assert_regex_format(rows, "email", EMAIL_REGEX, "Email")),
            ("Phone Regex Pattern Format", lambda: DataValidator.assert_regex_format(rows, "phone", PHONE_REGEX, "Phone")),
            ("Statistical Data Drift Test (MMK)", lambda: DataValidator.assert_no_statistical_drift(base_rows, rows, "amount_mmk", max_z_score=3.0))
        ]

        results = []
        for name, fn in tests:
            r = fn()
            results.append({
                "test_name": name,
                "passed": r.passed,
                "message": r.message,
                "violations_count": len(r.violations),
                "sample_violations": r.violations[:8]
            })

        self.send_json_response({
            "filename": "Custom_Uploaded_Payload.csv",
            "total_rows": len(rows),
            "results": results,
            "passed_count": sum(1 for r in results if r["passed"]),
            "failed_count": sum(1 for r in results if not r["passed"]),
            "audited_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def send_json_response(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_response(404)
            self.end_headers()
            return

        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

def run_server(port=8082):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, DataSentinelHandler)
    print("=" * 70)
    print(f"  DataSentinel QA - Advanced Server Running on http://localhost:{port}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
