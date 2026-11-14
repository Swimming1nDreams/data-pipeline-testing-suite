"""
DataSentinel QA - Interactive Web Server
Provides a live REST API and Web Console on port 8082 for automated testing,
interactive auditing, and ETL pipeline inspection.
"""

import os
import sys
import json
import csv
import time
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
        elif path == "/" or path == "/index.html":
            self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html")
        else:
            super().do_GET()

    def handle_run_pytest(self):
        t0 = time.time()
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
        res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        duration = round(time.time() - t0, 2)

        data = {
            "output": res.stdout or res.stderr,
            "returncode": res.returncode,
            "duration": f"{duration}s"
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

        # Baseline rows for drift comparison
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
                "violations_count": len(r.violations)
            })

        self.send_json_response(results)

    def handle_etl(self, query):
        filename = query.get("file", ["incoming_corrupted_batch.csv"])[0]
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            self.send_json_response({"error": "File not found"}, 404)
            return

        pipeline = ETLPipeline()
        report = pipeline.process_batch(filepath)
        self.send_json_response(report)

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
    print(f"  DataSentinel QA - Web Console Running Live")
    print(f"  URL: http://localhost:{port}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
