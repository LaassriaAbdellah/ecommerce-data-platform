"""Structural checks and separate business indicators for Olist payments."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.validation.common import (
    check_duplicate_ids,
    check_missing_ids,
    check_required_columns,
)
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"

REQUIRED_COLUMNS = [
    "order_id", "payment_sequential", "payment_type",
    "payment_installments", "payment_value",
]


def validate_payments(payments: pd.DataFrame, orders: pd.DataFrame):
    """Flag structural issues, preserving inputs; keep indicators separate.

    Numeric conversions serve checks/keys only. Types must be nonempty, but
    no closed category list is imposed. Amounts are never multiplied.
    """
    check_required_columns(payments, REQUIRED_COLUMNS)
    check_required_columns(orders, ["order_id"])
    missing_order_id = check_missing_ids(payments, "order_id")
    numeric_columns = [
        "payment_sequential", "payment_installments", "payment_value"
    ]
    numeric = payments[numeric_columns].apply(pd.to_numeric, errors="coerce")
    finite = (numeric.notna() & np.isfinite(numeric)).fillna(False)
    for column in numeric_columns:
        # Booleans are not valid counts or monetary values.
        boolean_values = payments[column].map(
            lambda value: isinstance(value, (bool, np.bool_))
        ).astype(bool)
        finite[column] &= ~boolean_values

    sequence = numeric["payment_sequential"]
    installments = numeric["payment_installments"]
    value = numeric["payment_value"]
    valid_sequence = (
        finite["payment_sequential"]
        & sequence.gt(0)
        & sequence.where(finite["payment_sequential"]).mod(1).eq(0)
    ).fillna(False)
    valid_installments = (
        finite["payment_installments"]
        & installments.ge(0)
        & installments.where(finite["payment_installments"]).mod(1).eq(0)
    ).fillna(False)
    valid_value = (finite["payment_value"] & value.ge(0)).fillna(False)

    # "1" and 1 identify the same payment; original columns remain unchanged.
    keys = pd.DataFrame({
        "order_id": payments["order_id"],
        "payment_sequential": sequence,
    }, index=payments.index)
    valid_key = ~missing_order_id & valid_sequence
    rules = {
        "missing_order_id": missing_order_id,
        "duplicate_order_payment": (
            check_duplicate_ids(keys, ["order_id", "payment_sequential"])
            & valid_key
        ),
        "unknown_order": (
            ~payments["order_id"].isin(orders["order_id"].dropna())
            & ~missing_order_id
        ),
        "invalid_payment_sequential": ~valid_sequence,
        "invalid_payment_installments": ~valid_installments,
        "invalid_payment_value": ~valid_value,
        "missing_payment_type": check_missing_ids(payments, "payment_type"),
    }
    result, report = apply_quality_rules(payments, rules, entity_name="payments")

    # Do not infer a group's start if it includes an invalid/missing counter.
    minimum_sequence = keys.loc[valid_key].groupby("order_id")[
        "payment_sequential"
    ].min()
    invalid_sequence_orders = payments.loc[
        ~missing_order_id & ~valid_sequence, "order_id"
    ].unique()
    minimum_sequence = minimum_sequence.drop(
        index=invalid_sequence_orders, errors="ignore"
    )
    report["business_indicators"] = {
        "zero_payment_value_rows": int((valid_value & value.eq(0)).sum()),
        "zero_payment_installments_rows": int(
            (valid_installments & installments.eq(0)).sum()
        ),
        "not_defined_payment_type_rows": int(
            payments["payment_type"].eq("not_defined").fillna(False).sum()
        ),
        "orders_sequence_not_starting_at_1": int(minimum_sequence.ne(1).sum()),
    }
    return result, report


def main():
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv", usecols=["order_id"]
    )
    validated_payments, report = validate_payments(payments, orders)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validated_payments.to_csv(OUTPUT_DIR / "payments_validated.csv", index=False)
    with (OUTPUT_DIR / "payments_quality_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    print("\n=== RAPPORT DE QUALITÉ PAYMENTS ===")
    print("Lignes analysées :", report["total_rows"])
    print("Sans anomalie détectée :", report["valid_rows"])
    print("À examiner :", report["review_rows"])
    print("\nAnomalies structurelles par règle :")
    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")
    print("\nIndicateurs métier (sans effet sur la qualité) :")
    for name, count in report["business_indicators"].items():
        print(f"  {name}: {count}")
    print("\nRésultats enregistrés dans :", OUTPUT_DIR)


if __name__ == "__main__":
    main()
