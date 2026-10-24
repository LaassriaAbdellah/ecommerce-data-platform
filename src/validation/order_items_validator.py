"""Structural quality checks for Olist order items."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.validation.common import (
    check_duplicate_ids,
    check_invalid_dates,
    check_missing_ids,
    check_required_columns,
)
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"

REQUIRED_COLUMNS = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "shipping_limit_date",
    "price",
    "freight_value",
]


def _numeric_values(series: pd.Series):
    """Return numeric values and a mask excluding missing/non-finite/boolean data."""
    values = pd.to_numeric(series, errors="coerce")
    boolean_values = series.map(
        lambda value: isinstance(value, (bool, np.bool_))
    ).astype(bool)
    finite = (
        values.notna() & np.isfinite(values) & ~boolean_values
    ).fillna(False)
    return values, finite


def validate_order_items(
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
):
    """Flag structural issues without changing inputs or removing any rows.

    Monetary and item-number source values are preserved in the returned copy.
    Numeric conversion is only used for checks and composite-key comparison.
    Chronological/operational indicators are deliberately outside these rules.
    """
    check_required_columns(order_items, REQUIRED_COLUMNS)
    check_required_columns(orders, ["order_id"])

    missing_order_id = check_missing_ids(order_items, "order_id")
    missing_shipping_date = check_missing_ids(order_items, "shipping_limit_date")
    df, date_rules = check_invalid_dates(
        order_items, ["shipping_limit_date"], date_format="mixed"
    )

    item_numbers, finite_items = _numeric_values(order_items["order_item_id"])
    valid_item_number = (
        finite_items
        & item_numbers.gt(0)
        & item_numbers.where(finite_items).mod(1).eq(0)
    ).fillna(False)
    prices, finite_prices = _numeric_values(order_items["price"])
    freight, finite_freight = _numeric_values(order_items["freight_value"])

    # Compare numeric-equivalent item numbers, without changing the source column.
    keys = pd.DataFrame({
        "order_id": order_items["order_id"],
        "order_item_id": item_numbers,
    }, index=order_items.index)
    duplicate_key = (
        check_duplicate_ids(keys, ["order_id", "order_item_id"])
        & ~missing_order_id
        & valid_item_number
    )

    rules = {
        "missing_order_id": missing_order_id,
        "missing_product_id": check_missing_ids(order_items, "product_id"),
        "missing_seller_id": check_missing_ids(order_items, "seller_id"),
        "duplicate_order_item": duplicate_key,
        "invalid_order_item_id": ~valid_item_number,
        "unknown_order": (
            ~order_items["order_id"].isin(orders["order_id"].dropna())
            & ~missing_order_id
        ),
        "invalid_price": ~(finite_prices & prices.gt(0)).fillna(False),
        "invalid_freight_value": ~(finite_freight & freight.ge(0)).fillna(False),
        "missing_shipping_limit_date": missing_shipping_date,
        "invalid_shipping_limit_date": (
            date_rules["invalid_shipping_limit_date"] & ~missing_shipping_date
        ),
    }
    return apply_quality_rules(df, rules, entity_name="order_items")


def main():
    order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv", usecols=["order_id"]
    )
    validated_items, report = validate_order_items(order_items, orders)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validated_items.to_csv(OUTPUT_DIR / "order_items_validated.csv", index=False)
    with (OUTPUT_DIR / "order_items_quality_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n=== RAPPORT DE QUALITÉ ORDER ITEMS ===")
    print("Lignes analysées :", report["total_rows"])
    print("Sans anomalie détectée :", report["valid_rows"])
    print("À examiner :", report["review_rows"])
    print("\nAnomalies par règle :")
    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")
    print("\nRésultats enregistrés dans :", OUTPUT_DIR)


if __name__ == "__main__":
    main()
