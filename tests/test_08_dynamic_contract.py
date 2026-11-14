import pytest
from core.contract import DataContract

def test_contract_inference():
    sample_rows = [
        {"emp_id": "EMP_01", "name": "Aung Aung", "age": "28", "salary": "1500000.0", "department": "Engineering", "phone": "09250123456"},
        {"emp_id": "EMP_02", "name": "Su Su", "age": "32", "salary": "1800000.0", "department": "Marketing", "phone": "09450012345"},
        {"emp_id": "EMP_03", "name": "Kyaw Kyaw", "age": "24", "salary": "1200000.0", "department": "Engineering", "phone": "09791112223"}
    ]

    contract = DataContract.infer_contract(sample_rows, dataset_name="EmployeePayroll")
    assert contract["dataset"] == "EmployeePayroll"
    assert contract["primary_key"] == "emp_id"

    cols = contract["columns"]
    assert cols["age"]["type"] == "integer"
    assert cols["age"]["min"] == 24
    assert cols["age"]["max"] == 32
    assert cols["salary"]["type"] == "float"
    assert cols["phone"]["type"] == "phone"
    assert cols["department"]["type"] == "enum"
    assert "Engineering" in cols["department"]["allowed_values"]

def test_contract_validation_passes_clean_data():
    sample_rows = [
        {"order_id": "ORD_1", "qty": "5", "phone": "09250123456", "category": "Retail"},
        {"order_id": "ORD_2", "qty": "10", "phone": "09450012345", "category": "Wholesale"}
    ]
    contract = DataContract.infer_contract(sample_rows, dataset_name="Orders")
    results = DataContract.validate(sample_rows, contract)
    assert all(r.passed for r in results)

def test_contract_validation_catches_violations():
    contract = {
        "dataset": "TestOrders",
        "primary_key": "order_id",
        "columns": {
            "order_id": {"type": "string", "nullable": False},
            "qty": {"type": "integer", "min": 1, "max": 100, "nullable": False},
            "category": {"type": "enum", "allowed_values": ["Retail", "Wholesale"], "nullable": False}
        }
    }

    violating_rows = [
        {"order_id": "ORD_1", "qty": "5", "category": "Retail"},
        {"order_id": "ORD_1", "qty": "250", "category": "Unknown_Category"}, # Duplicate PK, qty > 100, invalid category
        {"order_id": "ORD_3", "qty": "", "category": "Wholesale"} # Missing qty
    ]

    results = DataContract.validate(violating_rows, contract)
    failed_results = [r for r in results if not r.passed]
    assert len(failed_results) >= 3

    test_names = [r.test_name for r in failed_results]
    assert any("Primary Key Uniqueness" in name for name in test_names)
    assert any("Boundary Range [qty]" in name for name in test_names)
    assert any("Taxonomy Enum [category]" in name for name in test_names)
