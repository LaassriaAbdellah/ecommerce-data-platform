import hashlib
import json

import pandas as pd
import pytest

from src.validation import payments_validator as validator
from src.validation.payments_validator import REQUIRED_COLUMNS, validate_payments


def make_data():
    payments = pd.DataFrame({
        "order_id": ["O1", "O1"],
        "payment_sequential": [1, 2],
        "payment_type": ["credit_card", "voucher"],
        "payment_installments": [1, 1],
        "payment_value": [100.0, 20.0],
    })
    return payments, pd.DataFrame({"order_id": ["O1", "O2"]})


def with_value(payments, column, value):
    result = payments.copy()
    result[column] = result[column].astype(object)
    result.loc[0, column] = value
    return result


def test_normal_payment():
    payments, orders = make_data()
    result, report = validate_payments(payments.iloc[[0]], orders)
    assert report["entity"] == "payments"
    assert report["total_rows"] == report["valid_rows"] == 1
    assert report["review_rows"] == 0
    assert result.iloc[0]["quality_status"] == "valid"
    assert result.iloc[0]["quality_issue_count"] == 0
    assert json.loads(result.iloc[0]["quality_issues"]) == []


def test_two_payments_for_one_order():
    payments, orders = make_data()
    result, report = validate_payments(payments, orders)
    assert report["valid_rows"] == 2
    assert report["review_rows"] == 0
    assert report["anomalies_by_rule"]["duplicate_order_payment"] == 0
    assert result["payment_value"].sum() == 120


@pytest.mark.parametrize("second", [1, "1"])
def test_duplicate_composite_key(second):
    payments, orders = make_data()
    payments["payment_sequential"] = pd.Series([1, second], dtype=object)
    result, report = validate_payments(payments, orders)
    assert report["review_rows"] == 2
    assert report["anomalies_by_rule"]["duplicate_order_payment"] == 2
    assert result["quality_issues"].map(json.loads).tolist() == [
        ["duplicate_order_payment"], ["duplicate_order_payment"]
    ]


def test_same_sequence_different_orders():
    payments, orders = make_data()
    payments.loc[1, "order_id"] = "O2"
    payments["payment_sequential"] = [1, 1]
    _, report = validate_payments(payments, orders)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", ["order_id", "payment_type"])
@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing_required_value(column, value):
    payments, orders = make_data()
    _, report = validate_payments(with_value(payments, column, value), orders)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"][f"missing_{column}"] == 1
    if column == "order_id":
        assert report["anomalies_by_rule"]["unknown_order"] == 0


def test_unknown_order():
    payments, orders = make_data()
    payments.loc[0, "order_id"] = "UNKNOWN"
    _, report = validate_payments(payments, orders)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"]["unknown_order"] == 1


@pytest.mark.parametrize("column", [
    "payment_sequential", "payment_installments", "payment_value"
])
@pytest.mark.parametrize("value", [
    -1, "bad", None, pd.NA, "", float("nan"),
    float("inf"), -float("inf"), "inf", True, False,
])
def test_invalid_numeric_values(column, value):
    payments, orders = make_data()
    _, report = validate_payments(with_value(payments, column, value), orders)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1
    if column == "payment_value":
        assert report["business_indicators"]["zero_payment_value_rows"] == 0
    if column == "payment_sequential":
        assert report["business_indicators"]["orders_sequence_not_starting_at_1"] == 0


@pytest.mark.parametrize("column", ["payment_sequential", "payment_installments"])
def test_fractional_counter(column):
    payments, orders = make_data()
    _, report = validate_payments(with_value(payments, column, 1.5), orders)
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1


def test_zero_sequence_is_invalid():
    payments, orders = make_data()
    payments.loc[0, "payment_sequential"] = 0
    _, report = validate_payments(payments, orders)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"]["invalid_payment_sequential"] == 1


@pytest.mark.parametrize("column,indicator", [
    ("payment_value", "zero_payment_value_rows"),
    ("payment_installments", "zero_payment_installments_rows"),
])
@pytest.mark.parametrize("value", [0, 0.0, "0", "0.00"])
def test_zero_value_is_valid_business_indicator(column, indicator, value):
    payments, orders = make_data()
    result, report = validate_payments(with_value(payments, column, value), orders)
    assert report["review_rows"] == 0
    assert report["business_indicators"][indicator] == 1
    assert result["quality_issue_count"].eq(0).all()


@pytest.mark.parametrize("payment_type,indicator", [
    ("not_defined", 1), ("new_type", 0)
])
def test_nonempty_type_is_accepted(payment_type, indicator):
    payments, orders = make_data()
    payments.loc[0, "payment_type"] = payment_type
    _, report = validate_payments(payments, orders)
    assert report["review_rows"] == 0
    assert report["business_indicators"]["not_defined_payment_type_rows"] == indicator


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
def test_missing_required_column(column):
    payments, orders = make_data()
    with pytest.raises(ValueError, match=column):
        validate_payments(payments.drop(columns=[column]), orders)


def test_missing_orders_reference_column():
    payments, _ = make_data()
    with pytest.raises(ValueError, match="order_id"):
        validate_payments(payments, pd.DataFrame({"other": ["O1"]}))


@pytest.mark.parametrize("column,value", [
    ("order_id", None), ("payment_sequential", 0)
])
def test_invalid_keys_not_counted_as_duplicates(column, value):
    payments, orders = make_data()
    payments = pd.concat([payments.iloc[[0]], payments.iloc[[0]]], ignore_index=True)
    payments[column] = value
    _, report = validate_payments(payments, orders)
    assert report["review_rows"] == 2
    assert report["anomalies_by_rule"]["duplicate_order_payment"] == 0


@pytest.mark.parametrize("sequences,expected", [([2, 3], 1), ([1, 3], 0)])
def test_sequence_start_indicator(sequences, expected):
    payments, orders = make_data()
    payments["payment_sequential"] = sequences
    result, report = validate_payments(payments, orders)
    assert report["business_indicators"]["orders_sequence_not_starting_at_1"] == expected
    assert report["review_rows"] == 0
    assert result["quality_issue_count"].eq(0).all()


def test_business_indicators_never_add_quality_issues():
    payments, orders = make_data()
    payments["payment_sequential"] = [2, 3]
    payments.loc[0, "payment_value"] = 0
    payments.loc[0, "payment_installments"] = 0
    payments.loc[0, "payment_type"] = "not_defined"
    result, report = validate_payments(payments, orders)
    assert report["business_indicators"] == {
        "zero_payment_value_rows": 1,
        "zero_payment_installments_rows": 1,
        "not_defined_payment_type_rows": 1,
        "orders_sequence_not_starting_at_1": 1,
    }
    assert report["review_rows"] == sum(report["anomalies_by_rule"].values()) == 0
    assert result["quality_issue_count"].eq(0).all()
    assert result["quality_issues"].map(json.loads).tolist() == [[], []]


def test_multiple_issues_count_one_row():
    payments, orders = make_data()
    payments.loc[0, "payment_value"] = -1
    payments = with_value(payments, "payment_type", None)
    result, report = validate_payments(payments, orders)
    assert report["review_rows"] == report["valid_rows"] == 1
    issues = json.loads(result.loc[0, "quality_issues"])
    assert set(issues) == {"invalid_payment_value", "missing_payment_type"}
    assert len(issues) == result.loc[0, "quality_issue_count"] == 2


def test_installments_never_multiply_amount():
    payments, orders = make_data()
    payments.loc[0, "payment_installments"] = 12
    result, report = validate_payments(payments, orders)
    assert result.loc[0, "payment_value"] == 100
    assert report["review_rows"] == 0


def test_inputs_and_index_preserved():
    payments, orders = make_data()
    payments.index = [10, 20]
    before_payments, before_orders = payments.copy(deep=True), orders.copy(deep=True)
    result, _ = validate_payments(payments, orders)
    pd.testing.assert_frame_equal(payments, before_payments)
    pd.testing.assert_frame_equal(orders, before_orders)
    assert result.index.tolist() == [10, 20]


def test_empty_payments():
    payments, orders = make_data()
    result, report = validate_payments(payments.iloc[:0], orders)
    assert result.empty
    assert report["total_rows"] == report["valid_rows"] == report["review_rows"] == 0
    assert all(value == 0 for value in report["business_indicators"].values())


def test_main_exports_without_changing_sources(tmp_path, monkeypatch):
    payments, orders = make_data()
    payments.loc[0, "payment_value"] = 0
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    payments_path = data_dir / "olist_order_payments_dataset.csv"
    orders_path = data_dir / "olist_orders_dataset.csv"
    payments.to_csv(payments_path, index=False)
    orders.to_csv(orders_path, index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (payments_path, orders_path)}
    monkeypatch.setattr(validator, "DATA_DIR", data_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", data_dir / "processed")

    validator.main()

    report = json.loads((data_dir / "processed/payments_quality_report.json").read_text(
        encoding="utf-8"
    ))
    saved = pd.read_csv(data_dir / "processed/payments_validated.csv")
    assert report["total_rows"] == report["valid_rows"] == len(saved) == 2
    assert report["review_rows"] == 0
    assert report["business_indicators"]["zero_payment_value_rows"] == 1
    assert saved["quality_status"].eq("valid").all()
    assert "business_indicators" not in report["anomalies_by_rule"]
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
