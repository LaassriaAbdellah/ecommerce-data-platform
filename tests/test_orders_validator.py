import json

import pandas as pd

from src.validation.orders_validator import validate_orders


def make_data():
    orders = pd.DataFrame({
        "order_id": ["O1", "O2"],
        "customer_id": ["C1", "C2"],
        "order_status": ["delivered", "canceled"],
        "order_purchase_timestamp": [
            "2018-01-01", "2018-01-02"
        ],
        "order_approved_at": [
            "2018-01-01", None
        ],
        "order_delivered_carrier_date": [
            "2018-01-03", None
        ],
        "order_delivered_customer_date": [
            "2018-01-05", None
        ],
        "order_estimated_delivery_date": [
            "2018-01-08", "2018-01-09"
        ],
    })

    customers = pd.DataFrame({
        "customer_id": ["C1", "C2"]
    })

    return orders, customers


def test_valid_orders():
    orders, customers = make_data()

    result, report = validate_orders(orders, customers)

    assert report["total_orders"] == 2
    assert report["review_orders"] == 0
    assert result["quality_status"].eq("valid").all()


def test_missing_delivery_date():
    orders, customers = make_data()

    orders.loc[0, "order_delivered_customer_date"] = None

    result, report = validate_orders(orders, customers)

    assert report["anomalies_by_rule"]["missing_delivery_date"] == 1
    assert report["review_orders"] == 1
    assert result.loc[0, "quality_status"] == "review"


def test_shipping_before_purchase():
    orders, customers = make_data()

    orders.loc[0, "order_delivered_carrier_date"] = "2017-12-30"

    result, report = validate_orders(orders, customers)

    assert report["anomalies_by_rule"]["shipping_before_purchase"] == 1
    assert report["review_orders"] == 1


def test_unknown_customer():
    orders, customers = make_data()

    orders.loc[0, "customer_id"] = "UNKNOWN"

    result, report = validate_orders(orders, customers)

    assert report["anomalies_by_rule"]["unknown_customer"] == 1
    assert report["review_orders"] == 1


def test_multiple_issues_count_order_once():
    orders, customers = make_data()
    orders.loc[0, "order_delivered_customer_date"] = None
    orders.loc[0, "customer_id"] = "UNKNOWN"

    result, report = validate_orders(orders, customers)

    assert report["total_orders"] == 2
    assert report["review_orders"] == 1
    assert report["valid_orders"] == 1
    assert result.loc[0, "quality_status"] == "review"
    assert result.loc[0, "quality_issue_count"] == 2
    issues = json.loads(result.loc[0, "quality_issues"])
    assert len(issues) == 2
    assert set(issues) == {"missing_delivery_date", "unknown_customer"}
    assert report["anomalies_by_rule"]["missing_delivery_date"] == 1
    assert report["anomalies_by_rule"]["unknown_customer"] == 1
    assert sum(report["anomalies_by_rule"].values()) == 2
    assert result.loc[1, "quality_status"] == "valid"
    assert result.loc[1, "quality_issue_count"] == 0
    assert json.loads(result.loc[1, "quality_issues"]) == []
