"""
Pytest Test Fixtures for DataSentinel QA
Provides clean and corrupted dataset fixtures, database setups, and tear-downs.
"""

import os
import csv
import pytest
from core.synthetic_generator import generate_clean_baseline, generate_corrupted_batch
from core.pipeline import ETLPipeline

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_csv_as_dicts(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@pytest.fixture(scope="session")
def clean_data_path():
    path = os.path.join(DATA_DIR, "baseline_clean.csv")
    if not os.path.exists(path):
        generate_clean_baseline(count=500, filepath=path)
    return path

@pytest.fixture(scope="session")
def corrupted_data_path():
    path = os.path.join(DATA_DIR, "incoming_corrupted_batch.csv")
    if not os.path.exists(path):
        generate_corrupted_batch(count=300, filepath=path)
    return path

@pytest.fixture(scope="session")
def clean_records(clean_data_path):
    return _load_csv_as_dicts(clean_data_path)

@pytest.fixture(scope="session")
def corrupted_records(corrupted_data_path):
    return _load_csv_as_dicts(corrupted_data_path)

@pytest.fixture
def temp_pipeline(tmp_path):
    db_file = tmp_path / "test_warehouse.db"
    return ETLPipeline(db_path=str(db_file))
