"""
Test Suite 05: End-to-End ETL Pipeline & Dead-Letter Quarantine Tests
Tests end-to-end batch ingestion, database persistence, and isolation of dirty records.
"""

import sqlite3

def test_pipeline_clean_batch_ingestion(clean_data_path, temp_pipeline):
    """Assertion: Clean batch processes with 100% acceptance and zero quarantine."""
    report = temp_pipeline.process_batch(clean_data_path)
    assert report["total_processed"] > 0
    assert report["clean_committed"] == report["total_processed"]
    assert report["quarantined_count"] == 0
    assert report["clean_ratio"] == 100.0

    # Verify directly in SQLite
    conn = sqlite3.connect(temp_pipeline.db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM clean_transactions")
    count = cur.fetchone()[0]
    conn.close()
    assert count == report["clean_committed"]

def test_pipeline_corrupted_batch_quarantine_isolation(corrupted_data_path, temp_pipeline):
    """Assertion: Dirty batch does NOT crash the pipeline; bad records are quarantined with audit trail."""
    report = temp_pipeline.process_batch(corrupted_data_path)
    assert report["total_processed"] > 0
    assert report["quarantined_count"] > 0
    assert report["clean_committed"] > 0
    assert report["clean_ratio"] < 100.0

    # Verify dead-letter quarantine table
    conn = sqlite3.connect(temp_pipeline.db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*), failed_field FROM quarantine_audit GROUP BY failed_field")
    quarantine_summary = cur.fetchall()
    conn.close()

    failed_fields = [f[1] for f in quarantine_summary]
    assert "customer_id" in failed_fields # null check
    assert "age" in failed_fields         # range check
    assert "township" in failed_fields    # enum check
