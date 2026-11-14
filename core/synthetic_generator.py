"""
DataSentinel QA - Synthetic Dataset Generator
Generates clean baseline datasets and realistic corrupted test batches with injected anomalies.
"""

import os
import random
import csv
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

TOWNSHIPS = ["Hinthada", "Zalun", "Danubyu", "Myanaung", "Kyangin", "Ingapu"]
PAYMENT_TYPES = ["Mobile_Wallet", "Bank_Transfer", "Cash_Agent", "Direct_Deposit"]
STATUSES = ["COMPLETED", "PENDING", "RECONCILED", "FLAGGED"]

def generate_clean_baseline(count=1000, filepath=None):
    """Generates a clean baseline dataset representing production standard."""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "baseline_clean.csv")
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    random.seed(42) # Deterministic for testing repeatability
    
    records = []
    base_date = datetime(2026, 1, 1)
    
    for i in range(1, count + 1):
        dt = base_date + timedelta(days=random.randint(0, 90), minutes=random.randint(0, 1440))
        record = {
            "transaction_id": f"TXN-{i:06d}",
            "customer_id": f"CUST-{random.randint(100, 500):04d}",
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "township": random.choice(TOWNSHIPS),
            "age": random.randint(18, 65),
            "amount_mmk": round(random.uniform(50000, 750000), 2),
            "payment_type": random.choice(PAYMENT_TYPES),
            "email": f"user{i:04d}@domain.org",
            "phone": f"+959{random.randint(20000000, 99999999)}",
            "status": random.choice(["COMPLETED", "RECONCILED"]),
            "anomaly_flag": 0
        }
        records.append(record)
        
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[Generator] Clean baseline generated: {filepath} ({count} rows)")
    return filepath

def generate_corrupted_batch(count=300, filepath=None):
    """Generates an incoming test batch with injected anomalies for automated QA testing."""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "incoming_corrupted_batch.csv")
        
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    random.seed(101)
    
    records = []
    base_date = datetime(2026, 4, 1)
    
    for i in range(1, count + 1):
        dt = base_date + timedelta(days=random.randint(0, 30))
        
        txn_id = f"TXN-{1000 + i:06d}"
        cust_id = f"CUST-{random.randint(100, 500):04d}"
        township = random.choice(TOWNSHIPS)
        age = random.randint(18, 65)
        amount = round(random.uniform(50000, 750000), 2)
        payment = random.choice(PAYMENT_TYPES)
        email = f"client{i:04d}@partner.net"
        phone = f"+959{random.randint(20000000, 99999999)}"
        status = random.choice(STATUSES)
        anomaly_type = "NONE"
        
        # Inject Specific Edge Cases for Testing Assertions:
        
        # 1. Null Value Injections (Rows 10-15)
        if 10 <= i <= 15:
            customer_id = "" # Missing required key
            anomaly_type = "MISSING_CUSTOMER_ID"
        else:
            customer_id = cust_id
            
        # 2. Out-of-bounds Age (Rows 25-28)
        if 25 <= i <= 28:
            age = random.choice([-5, 0, 145]) # Negative / Extreme age
            anomaly_type = "INVALID_AGE_RANGE"
            
        # 3. Duplicate Primary Key Collision (Row 40 duplicates Row 39)
        if i == 40 and len(records) > 0:
            txn_id = records[-1]["transaction_id"]
            anomaly_type = "DUPLICATE_PRIMARY_KEY"
            
        # 4. Negative Transaction Amount (Rows 60-62)
        if 60 <= i <= 62:
            amount = -150000.00 # Impossible negative cash
            anomaly_type = "NEGATIVE_AMOUNT"
            
        # 5. Invalid Enum / Unrecognized Category (Rows 80-82)
        if 80 <= i <= 82:
            township = "Unknown_Galaxy_Zone" # Outside valid taxonomy
            anomaly_type = "INVALID_CATEGORY_ENUM"
            
        # 6. Malformed Email & Phone Regex Violation (Rows 110-113)
        if 110 <= i <= 113:
            email = "not_an_email_at_all"
            phone = "123-BAD-PHONE"
            anomaly_type = "REGEX_FORMAT_ERROR"
            
        # 7. Statistical Drift: Massive amount spike (Rows 250-280)
        if 250 <= i <= 280:
            amount = round(random.uniform(15000000, 35000000), 2) # 50x mean shift
            anomaly_type = "STATISTICAL_OUTLIER"

        record = {
            "transaction_id": txn_id,
            "customer_id": customer_id,
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "township": township,
            "age": age,
            "amount_mmk": amount,
            "payment_type": payment,
            "email": email,
            "phone": phone,
            "status": status,
            "injected_anomaly": anomaly_type
        }
        records.append(record)
        
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[Generator] Corrupted test batch generated: {filepath} ({count} rows, injected anomalies)")
    return filepath

if __name__ == "__main__":
    generate_clean_baseline()
    generate_corrupted_batch()
