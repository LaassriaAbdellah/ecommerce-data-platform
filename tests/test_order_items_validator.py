import hashlib
import json

import pandas as pd
import pytest

from src.validation import order_items_validator as validator
from src.validation.order_items_validator import (
    REQUIRED_COLUMNS,
    validate_order_items,
)


def make_data():
    items = pd.DataFrame({
        "order_id": ["O1", "O1"],
        "order_item_id": [1, 2],
        "product_id": ["P1", "P2"],
        "seller_id": ["S1", "S2"],
        "shipping_limit_date": ["2018-01-10", "2018-01-11"],
        "price": [100.0, 50.0],
        "freight_value": [10.0, 5.0],
    })
    orders = pd.DataFrame({"order_id": ["O1", "O2"]})
    return items, orders


def with_value(items, column, value):
    # Object dtype lets tests represent malformed data without Pandas coercion.
    result = items.copy()
    result[column] = result[column].astype(object)
    result.loc[0, column] = value
    return result


def test_valid_items():
    items, orders = make_data()
    result, report = validate_order_items(items, orders)
    assert report["entity"] == "order_items"
    assert report["total_rows"] == report["valid_rows"] == 2
    assert report["review_rows"] == 0
    assert result["quality_status"].eq("valid").all()
    assert result["quality_issue_count"].eq(0).all()
    assert result["quality_issues"].map(json.loads).tolist() == [[], []]


@pytest.mark.parametrize("column", ["order_id", "product_id", "seller_id"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_identifier(column, value):
    items, orders = make_data()
    result, report = validate_order_items(with_value(items, column, value), orders)
    assert report["anomalies_by_rule"][f"missing_{column}"] == 1
    assert report["review_rows"] == 1
    assert result.loc[0, "quality_status"] == "review"
    if column == "order_id":
        assert report["anomalies_by_rule"]["unknown_order"] == 0


@pytest.mark.parametrize("second_number", [1, "1"])
def test_duplicate_composite_key(second_number):
    items, orders = make_data()
    items["order_item_id"] = pd.Series([1, second_number], dtype=object)
    result, report = validate_order_items(items, orders)
    assert report["anomalies_by_rule"]["duplicate_order_item"] == 2
    assert report["review_rows"] == 2
    assert result["quality_issues"].map(json.loads).tolist() == [
        ["duplicate_order_item"], ["duplicate_order_item"]
    ]


def test_same_item_number_in_different_orders_is_valid():
    items, orders = make_data()
    items.loc[1, "order_id"] = "O2"
    items["order_item_id"] = [1, 1]
    _, report = validate_order_items(items, orders)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("value", [
    0, -1, 1.5, "bad", None, pd.NA, "", float("inf"), -float("inf"), True,
])
def test_invalid_item_number(value):
    items, orders = make_data()
    _, report = validate_order_items(with_value(items, "order_item_id", value), orders)
    assert report["anomalies_by_rule"]["invalid_order_item_id"] == 1
    assert report["review_rows"] == 1


def test_unknown_order():
    items, orders = make_data()
    items.loc[0, "order_id"] = "UNKNOWN"
    _, report = validate_order_items(items, orders)
    assert report["anomalies_by_rule"]["unknown_order"] == 1
    assert report["review_rows"] == 1


@pytest.mark.parametrize("value", [
    0, -0.01, "bad", None, pd.NA, "", float("nan"),
    float("inf"), -float("inf"), "inf", True,
])
def test_invalid_price(value):
    items, orders = make_data()
    _, report = validate_order_items(with_value(items, "price", value), orders)
    assert report["anomalies_by_rule"]["invalid_price"] == 1
    assert report["review_rows"] == 1


@pytest.mark.parametrize("value", [
    -0.01, "bad", None, pd.NA, "", float("nan"),
    float("inf"), -float("inf"), True,
])
def test_invalid_freight(value):
    items, orders = make_data()
    _, report = validate_order_items(with_value(items, "freight_value", value), orders)
    assert report["anomalies_by_rule"]["invalid_freight_value"] == 1
    assert report["review_rows"] == 1


@pytest.mark.parametrize("value", [0, 0.0, "0", "0.00"])
def test_zero_freight_is_valid(value):
    items, orders = make_data()
    _, report = validate_order_items(with_value(items, "freight_value", value), orders)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("value", ["bad", "2018-02-30"])
def test_invalid_shipping_date(value):
    items, orders = make_data()
    result, report = validate_order_items(
        with_value(items, "shipping_limit_date", value), orders
    )
    assert report["anomalies_by_rule"]["invalid_shipping_limit_date"] == 1
    assert report["review_rows"] == 1
    assert pd.isna(result.loc[0, "shipping_limit_date"])


@pytest.mark.parametrize("value", [None, pd.NaT, "", "   "])
def test_missing_shipping_date(value):
    items, orders = make_data()
    _, report = validate_order_items(
        with_value(items, "shipping_limit_date", value), orders
    )
    assert report["anomalies_by_rule"]["missing_shipping_limit_date"] == 1
    assert report["anomalies_by_rule"]["invalid_shipping_limit_date"] == 0
    assert report["review_rows"] == 1


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
def test_missing_required_column(column):
    items, orders = make_data()
    with pytest.raises(ValueError, match=column):
        validate_order_items(items.drop(columns=[column]), orders)


def test_missing_orders_reference_column():
    items, _ = make_data()
    with pytest.raises(ValueError, match="order_id"):
        validate_order_items(items, pd.DataFrame({"other": ["O1"]}))


@pytest.mark.parametrize("column,value", [("order_id", None), ("order_item_id", 0)])
def test_incomplete_keys_are_not_reported_as_duplicates(column, value):
    items, orders = make_data()
    items = pd.concat([items.iloc[[0]], items.iloc[[0]]], ignore_index=True)
    items[column] = value
    _, report = validate_order_items(items, orders)
    assert report["anomalies_by_rule"]["duplicate_order_item"] == 0
    assert report["review_rows"] == 2


def test_multiple_issues_count_one_row():
    items, orders = make_data()
    items.loc[0, "price"] = 0
    items.loc[0, "freight_value"] = -1
    result, report = validate_order_items(items, orders)
    assert report["review_rows"] == 1
    assert report["valid_rows"] == 1
    issues = json.loads(result.loc[0, "quality_issues"])
    assert set(issues) == {"invalid_price", "invalid_freight_value"}
    assert len(issues) == result.loc[0, "quality_issue_count"] == 2


def test_inputs_unchanged_with_custom_index():
    items, orders = make_data()
    items.index = [10, 20]
    original_items, original_orders = items.copy(deep=True), orders.copy(deep=True)
    result, _ = validate_order_items(items, orders)
    pd.testing.assert_frame_equal(items, original_items)
    pd.testing.assert_frame_equal(orders, original_orders)
    assert result.index.tolist() == [10, 20]


def test_empty_items():
    items, orders = make_data()
    result, report = validate_order_items(items.iloc[:0], orders)
    assert result.empty
    assert report["total_rows"] == report["review_rows"] == report["valid_rows"] == 0


def test_chronological_indicators_do_not_mark_review():
    items, orders = make_data()
    # One deadline predates approval; the other is in 2020. Carrier dates are late.
    orders["order_approved_at"] = ["2018-02-01", "2018-02-01"]
    orders["order_delivered_carrier_date"] = ["2021-01-01", "2021-01-01"]
    items.loc[1, "shipping_limit_date"] = "2020-04-09 22:35:08"
    items.loc[0, "freight_value"] = 0
    _, report = validate_order_items(items, orders)
    assert report["review_rows"] == 0


def test_main_exports_without_changing_sources(tmp_path, monkeypatch):
    items, orders = make_data()
    data_dir = tmp_path / "data"
    output_dir = data_dir / "processed"
    data_dir.mkdir()
    items_path = data_dir / "olist_order_items_dataset.csv"
    orders_path = data_dir / "olist_orders_dataset.csv"
    items.to_csv(items_path, index=False)
    orders.to_csv(orders_path, index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (items_path, orders_path)}
    monkeypatch.setattr(validator, "DATA_DIR", data_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", output_dir)

    validator.main()

    report = json.loads((output_dir / "order_items_quality_report.json").read_text(
        encoding="utf-8"
    ))
    saved = pd.read_csv(output_dir / "order_items_validated.csv")
    assert report["total_rows"] == report["valid_rows"] == len(saved) == 2
    assert report["review_rows"] == 0
    assert saved["quality_status"].eq("valid").all()
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in before}
