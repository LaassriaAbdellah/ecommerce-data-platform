
import pandas as pd

from src.validation.customers_validator import validate_customers


def make_customers():
    return pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "customer_unique_id": ["U1", "U1"],
        "customer_zip_code_prefix": ["01234", "12345"],
        "customer_city": ["sao paulo", "rio de janeiro"],
        "customer_state": ["SP", "RJ"],
    })


def test_valid_customers():
    df = make_customers()

    result, report = validate_customers(df)

    assert report["total_rows"] == 2
    assert report["review_rows"] == 0
    assert result["quality_status"].eq("valid").all()


def test_duplicate_customer_id():
    df = make_customers()
    df.loc[1, "customer_id"] = "C1"

    _, report = validate_customers(df)

    assert report["anomalies_by_rule"]["duplicate_customer_id"] == 2


def test_invalid_zip_code():
    df = make_customers()
    df.loc[0, "customer_zip_code_prefix"] = "123"

    _, report = validate_customers(df)

    assert report["anomalies_by_rule"]["invalid_zip_code"] == 1


def test_invalid_customer_state():
    df = make_customers()
    df.loc[0, "customer_state"] = "XX"

    _, report = validate_customers(df)

    assert report["anomalies_by_rule"]["invalid_customer_state"] == 1


def test_repeated_unique_customer_is_valid():
    df = make_customers()

    _, report = validate_customers(df)

    assert report["review_rows"] == 0
