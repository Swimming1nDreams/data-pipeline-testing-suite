"""
DataSentinel QA - Interactive Web Server & REST API
Enhanced with Live Pytest runner, Statistical Distribution Bins, Quarantine Explorer,
and Custom CSV live audit engine.
"""

import os
import sys
import json
import csv
import time
import sqlite3
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

from core.validator import DataValidator
from core.pipeline import ETLPipeline, SCHEMA_CONTRACT, VALID_TOWNSHIPS, EMAIL_REGEX, PHONE_REGEX

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
        elif path == "/api/etl":
            self.handle_etl(query)
        elif path == "/api/quarantine-records":
            self.handle_quarantine_records()
        elif path == "/api/distribution-data":
            self.handle_distribution_data()
        elif path == "/" or path == "/index.html":
            self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload-audit":
            self.handle_upload_audit()
        else:
            self.send_response(404)
            self.end_headers()

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
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            self.send_json_response({"error": f"File {filename} not found"}, 404)
            return

        rows = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        base_path = os.path.join(DATA_DIR, "baseline_clean.csv")
        base_rows = []
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                base_rows = list(csv.DictReader(f))

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
                "sample_violations": r.violations[:8] # sample of failed rows
            })

        self.send_json_response({
            "filename": filename,
            "total_rows": len(rows),
            "results": results,
            "passed_count": sum(1 for r in results if r["passed"]),
            "failed_count": sum(1 for r in results if not r["passed"]),
            "audited_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

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
        """Calculates histogram bins for Baseline vs Corrupted batch for Chart.js visualization."""
        base_path = os.path.join(DATA_DIR, "baseline_clean.csv")
        batch_path = os.path.join(DATA_DIR, "incoming_corrupted_batch.csv")

        def get_amounts(path):
            if not os.path.exists(path): return []
            res = []
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    try: res.append(float(r["amount_mmk"]))
                    except: pass
            return res

        base_amt = get_amounts(base_path)
        batch_amt = get_amounts(batch_path)

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

    def handle_upload_audit(self):
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length).decode("utf-8")
        
        lines = [l for l in post_data.splitlines() if l.strip()]
        if len(lines) < 2:
            self.send_json_response({"error": "CSV requires header and at least one data row"}, 400)
            return

        reader = csv.DictReader(lines)
        rows = list(reader)

        base_path = os.path.join(DATA_DIR, "baseline_clean.csv")
        base_rows = []
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                base_rows = list(csv.DictReader(f))

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
            "filename": "Uploaded_Custom_Payload.csv",
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
    print(f"  DataSentinel QA - Enhanced Web Server Running")
    print(f"  URL: http://localhost:{port}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
