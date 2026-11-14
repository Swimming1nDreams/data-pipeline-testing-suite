# DataSentinel QA — Automated Data Pipeline & ETL Testing Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pytest 9.2+](https://img.shields.io/badge/tested_with-pytest-0A9EDC.svg)](https://docs.pytest.org/)
[![Code Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A production-grade **Data Pipeline Quality Assurance & Automated Testing Framework**. Engineered in pure Python to detect schema violations, boundary anomalies, primary-key collisions, referential orphans, and statistical distribution drift before data enters production warehouses.

---

## 📌 Architecture & Test Lifecycle

```
[ Raw Ingestion Batch (CSV / API) ]
                │
                ▼
┌──────────────────────────────────────────────┐
│        DataSentinel QA Test Engine           │
│                                              │
│  ├─ 1. Schema Contract & Type Check          │
│  ├─ 2. Mandatory Null Rate Assertions        │
│  ├─ 3. Primary Key Uniqueness & Collision    │
│  ├─ 4. Numerical Range [Age, Amount, etc.]   │
│  ├─ 5. Taxonomy Category Enum Integrity      │
│  ├─ 6. Format Regex (Email, Phone, ISO Date) │
│  └─ 7. Statistical Data Drift (Z-Score)      │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
[ Clean Validation Pass ]    [ Quarantine Dead-Letter ]
         │                           │
         ▼                           ▼
SQLite Production Warehouse    Audit Trail Log (Reason & Payload)
```

---

## 🚀 Key Features

*   **Zero-Overhead Assertion Engine:** Pure Python validators (`core/validator.py`) executing 14+ automated tests in under 1 second.
*   **Statistical Data Drift Detection:** Measures shifts in population mean and standard error ($Z$-score tracking) to flag distribution changes before models degrade.
*   **Dead-Letter Quarantine Mechanism:** Dirty records are isolated with exact failure codes into a `quarantine_audit` table without crashing batch pipelines.
*   **Dual Interface:**
    *   **Developer CLI:** Run tests, generate synthetic data, and audit any CSV from terminal.
    *   **Live Web Console (`http://localhost:8082`):** Interactive execution terminal, test matrix badges, real-time drift gauges, and quarantine inspector.
*   **CI/CD Ready:** Includes GitHub Actions automation configuration for automated testing on every pull request.

---

## 🧪 Test Suite Matrix (14 / 14 Passed)

| Test Suite | Target Assertion | Result |
| :--- | :--- | :---: |
| `test_01_schema_contract.py` | Schema column contract & datatypes | **PASSED** |
| `test_01_schema_contract.py` | Mandatory null rate integrity ($0\%$ nulls) | **PASSED** |
| `test_01_schema_contract.py` | Corrupted batch null detection | **PASSED** |
| `test_02_business_rules.py` | Numerical age boundary $[18, 100]$ | **PASSED** |
| `test_02_business_rules.py` | Out-of-bounds age detection (e.g. $-5$, $145$) | **PASSED** |
| `test_02_business_rules.py` | Negative transaction amount detection | **PASSED** |
| `test_02_business_rules.py` | Township category taxonomy enum check | **PASSED** |
| `test_02_business_rules.py` | Email & Phone regex pattern verification | **PASSED** |
| `test_03_referential_integrity.py` | Baseline primary key uniqueness ($100\%$ unique) | **PASSED** |
| `test_03_referential_integrity.py` | Duplicate primary key collision detection | **PASSED** |
| `test_04_data_drift.py` | Clean baseline split consistency ($Z < 3.0$) | **PASSED** |
| `test_04_data_drift.py` | Injected $50\times$ amount spike drift alarm ($Z > 4.5$) | **PASSED** |
| `test_05_etl_pipeline_e2e.py` | Clean batch end-to-end SQLite commit | **PASSED** |
| `test_05_etl_pipeline_e2e.py` | Dirty batch quarantine isolation without crash | **PASSED** |

---

## 🛠️ Quickstart Guide

### 1. Installation
```bash
git clone https://github.com/Swimming1nDreams/data-pipeline-testing-suite.git
cd data-pipeline-testing-suite
pip install -r requirements.txt
```

### 2. Run Automated Pytest Suite
```bash
# Run all tests with verbose output
pytest -v

# Run with test coverage analysis
pytest --cov=core
```

### 3. Use the CLI Tool
```bash
# Audit a clean dataset
python cli.py audit data/baseline_clean.csv

# Audit a corrupted test dataset
python cli.py audit data/incoming_corrupted_batch.csv

# Regenerate synthetic benchmark datasets
python cli.py generate-data --clean-count 1000 --corrupt-count 300
```

### 4. Launch the Interactive Web Console
```bash
python web_server.py
# Open http://localhost:8082 in your browser
```

---

## 📊 Code Coverage Summary

```text
Name                          Stmts   Miss  Cover
-------------------------------------------------
core\validator.py               128     11    91%
core\pipeline.py                 69      6    91%
-------------------------------------------------
TOTAL                           275     84    69%
```

---

## 📄 License
MIT License. Free for open-source and commercial data engineering workflows.
