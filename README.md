# DataSentinel QA — Enterprise Data Pipeline & Quality Testing Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pytest 9.2+](https://img.shields.io/badge/tested_with-pytest-0A9EDC.svg)](https://docs.pytest.org/)
[![Code Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A production-grade **Data Pipeline Quality Assurance, Automated Testing & Auto-Repair Framework**. Engineered in Python to detect schema violations, boundary anomalies, primary-key collisions, referential orphans, and statistical distribution drift before data enters production warehouses.

---

## 📌 Architecture & Test Lifecycle

```
[ Ingestion Batch: CSV / Excel (.xlsx) / API ]
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            DataSentinel QA Test & Repair Engine         │
│                                                         │
│  ├─ 1. Dynamic Schema Contract & Type Inference        │
│  ├─ 2. Myanmar Numeral Normalizer (၀-၉ -> 0-9)         │
│  ├─ 3. E.164 Phone (+959...) & ISO Date Standardization │
│  ├─ 4. Mandatory Null Integrity & Primary Key Checks    │
│  ├─ 5. Numerical Range Assertions [Age, Amount, etc.]   │
│  ├─ 6. Categorical Taxonomy Enum Verification           │
│  ├─ 7. Statistical Data Drift Detection (Z-Score)       │
│  └─ 8. PII Anonymization & Auto-Sanitization           │
└────────────────────────────┬────────────────────────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
      [ Clean Production Pass ]    [ Quarantine Dead-Letter ]
               │                           │
               ▼                           ▼
   • SQLite Data Warehouse        • `quarantine_audit` Table
   • Multi-Tab Excel (.xlsx)      • Granular Diagnostic Dossier
```

---

## 🚀 Key Features

*   **Zero-Overhead Assertion Engine:** Pure Python validators (`core/validator.py`) executing 24 automated tests in under 1 second.
*   **Dynamic Data Contract Studio (`core/contract.py`):** Automatically infers schema data types, nullability, unique keys, and boundaries from any arbitrary dataset without writing code.
*   **Enterprise Excel (.xlsx) Engine (`core/excel_io.py`):** Reads and generates beautifully styled, multi-sheet Excel audit reports (`Audit_Summary`, `Clean_Data`, and `Quarantine_Audit`) using `openpyxl`.
*   **Real-World Myanmar Normalization (`core/normalizer.py`):** Converts Burmese digits (`၀-၉` $\rightarrow$ `0-9`), standardizes phone numbers to international standard (`+959...`), detects Zawgyi fonts, and cleans irregular date formats to ISO-8601 (`YYYY-MM-DD`).
*   **Statistical Data Drift Detection:** Measures shifts in population mean and standard error ($Z$-score tracking) to flag distribution changes before downstream reporting or machine learning degradation.
*   **Dead-Letter Quarantine Mechanism:** Dirty records are isolated with exact failure diagnostics into a `quarantine_audit` table without crashing batch ETL pipelines.
*   **Multi-Interface Experience:**
    *   **Developer CLI:** Run tests, generate synthetic data, and audit any CSV or Excel file directly from terminal.
    *   **Native Windows Desktop Software (`app.py`):** Full standalone desktop window via `pywebview` with one-click desktop shortcut (`DataSentinel_QA.bat`).
    *   **Live Web Console (`http://localhost:8082`):** Glassmorphic dark dashboard with 10 operational tabs, visual rule builder, in-memory SQL sandbox, distribution charts, and upload studio.

---

## 🧪 Test Suite Matrix (24 / 24 Passed, 91% Coverage)

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
| `test_06_excel_io.py` | Multi-tab styled Excel (.xlsx) roundtrip generation & read | **PASSED** |
| `test_06_excel_io.py` | High-performance in-memory Excel byte stream export | **PASSED** |
| `test_07_normalizer_and_sanitizer.py` | Myanmar numerals normalization (`၀-၉` $\rightarrow$ `0-9`) | **PASSED** |
| `test_07_normalizer_and_sanitizer.py` | Phone number formatting to E.164 (`+959...`) | **PASSED** |
| `test_07_normalizer_and_sanitizer.py` | Multi-format date standardization to ISO `YYYY-MM-DD` | **PASSED** |
| `test_07_normalizer_and_sanitizer.py` | Zawgyi vs. Unicode font heuristic detection | **PASSED** |
| `test_07_normalizer_and_sanitizer.py` | Auto-repair engine repairing Burmese digits & phones in-place | **PASSED** |
| `test_08_dynamic_contract.py` | Dynamic contract auto-inference from arbitrary datasets | **PASSED** |
| `test_08_dynamic_contract.py` | Clean dataset validation against inferred contract | **PASSED** |
| `test_08_dynamic_contract.py` | Detection of range, type, and taxonomy violations against contracts | **PASSED** |

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
# Run all 24 tests
pytest -v

# Run with test coverage analysis (91% core coverage)
pytest --cov=core
```

### 3. Launch Desktop Software GUI
```bash
# Double click run_desktop.bat or run:
python app.py
```

### 4. Run Background Web API Server
```bash
python web_server.py
# Open http://localhost:8082 in your browser
```

---

## 📊 Project Structure

```
data_pipeline_testing_suite/
├── app.py                      # Desktop GUI launcher (pywebview)
├── run_desktop.bat             # 1-click Windows desktop launcher
├── web_server.py               # REST API & live server (port 8082)
├── cli.py                      # Developer terminal interface
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── core/                       # Core Data Engineering & QA Engine
│   ├── validator.py            # Quality assertions, nulls, ranges, Z-score drift
│   ├── contract.py             # Dynamic schema contract inference & validation
│   ├── excel_io.py             # Multi-tab styled Excel (.xlsx) I/O engine
│   ├── normalizer.py           # Myanmar digits, phone, date & Zawgyi normalizer
│   ├── sanitizer.py            # Auto-repair, PII masking, dead-letter quarantine
│   ├── profiler.py             # Automated column statistics & EDA metrics
│   ├── sql_sandbox.py          # In-memory SQLite SQL query runner (<20ms)
│   └── pipeline.py             # ETL batch processor & warehouse commit
├── tests/                      # Automated Test Suite (24 Tests)
│   ├── test_01_schema_contract.py
│   ├── test_02_business_rules.py
│   ├── test_03_referential_integrity.py
│   ├── test_04_data_drift.py
│   ├── test_05_etl_pipeline_e2e.py
│   ├── test_06_excel_io.py
│   ├── test_07_normalizer_and_sanitizer.py
│   └── test_08_dynamic_contract.py
└── public/
    └── index.html              # Glassmorphic Dark Dashboard UI
```

---

## 👤 Author & Maintainer

*   **Khant Si Thu** — B.C.Sc. (Software Engineering), University of Computer Studies, Hinthada (UCSH).
*   GitHub: [@Swimming1nDreams](https://github.com/Swimming1nDreams)
