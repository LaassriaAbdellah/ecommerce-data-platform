
from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"

DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "order_status",
    *DATE_COLUMNS,
]

VALID_STATUSES = {
    "created",
    "approved",
    "invoiced",
    "processing",
    "shipped",
    "delivered",
    "canceled",
    "unavailable",
}


def validate_orders(orders: pd.DataFrame,
                    customers: pd.DataFrame):
    """Valider les commandes sans modifier les données originales."""

    missing_columns = set(REQUIRED_COLUMNS) - set(orders.columns)
    if missing_columns:
        raise ValueError(
            f"Colonnes manquantes dans orders : {sorted(missing_columns)}"
        )

    if "customer_id" not in customers.columns:
        raise ValueError("customer_id absent de customers")

    df = orders.copy()

    # Vérifier les dates AVANT leur conversion.
    invalid_date_rules = {}

    for col in DATE_COLUMNS:
        original = df[col]
        converted = pd.to_datetime(original, errors="coerce")

        invalid_date_rules[f"invalid_{col}"] = (
            original.notna() & converted.isna()
        )

        df[col] = converted

    # Vérifier les identifiants.
    order_id_invalid = (
        df["order_id"].isna()
        | df["order_id"].astype("string").str.strip().eq("").fillna(False)
    )

    customer_id_invalid = (
        df["customer_id"].isna()
        | df["customer_id"].astype("string").str.strip().eq("").fillna(False)
    )

    # Contrôler les références clients.
    customer_references = customers["customer_id"].dropna()

    rules = {
        "missing_order_id": order_id_invalid,
        "missing_customer_id": customer_id_invalid,
        "duplicate_order_id": (
            df["order_id"].duplicated(keep=False)
            & ~order_id_invalid
        ),
        "unknown_customer": (
            ~df["customer_id"].isin(customer_references)
            & ~customer_id_invalid
        ),
        "invalid_order_status": (
            ~df["order_status"].isin(VALID_STATUSES)
        ),
        "missing_delivery_date": (
            df["order_status"].eq("delivered")
            & df["order_delivered_customer_date"].isna()
        ),
        "missing_approval_date": (
            df["order_status"].eq("delivered")
            & df["order_approved_at"].isna()
        ),
        "missing_carrier_date": (
            df["order_status"].eq("delivered")
            & df["order_delivered_carrier_date"].isna()
        ),
        "shipping_before_purchase": (
            df["order_delivered_carrier_date"]
            < df["order_purchase_timestamp"]
        ),
        "delivery_before_shipping": (
            df["order_delivered_customer_date"]
            < df["order_delivered_carrier_date"]
        ),
        "delivery_before_purchase": (
            df["order_delivered_customer_date"]
            < df["order_purchase_timestamp"]
        ),
        "estimated_delivery_before_purchase": (
            df["order_estimated_delivery_date"]
            < df["order_purchase_timestamp"]
        ),
        "delivery_before_approval": (
            df["order_delivered_customer_date"]
            < df["order_approved_at"]
        ),
        **invalid_date_rules,
    }

    checks = pd.DataFrame(rules, index=df.index).fillna(False).astype(bool)

    df["quality_issue_count"] = checks.sum(axis=1)

    df["quality_status"] = "valid"
    df.loc[df["quality_issue_count"] > 0, "quality_status"] = "review"

    # Une commande peut avoir plusieurs anomalies.
    df["quality_issues"] = [
        json.dumps(
            checks.columns[row.to_numpy()].tolist(),
            ensure_ascii=False
        )
        for _, row in checks.iterrows()
    ]

    report = {
        "total_orders": int(len(df)),
        "valid_orders": int(df["quality_status"].eq("valid").sum()),
        "review_orders": int(df["quality_status"].eq("review").sum()),
        "anomalies_by_rule": {
            name: int(count)
            for name, count in checks.sum().items()
        },
        "duplicate_customer_ids_in_customers": int(
            customers["customer_id"].duplicated().sum()
        ),
    }

    return df, report


def main():
    orders_path = DATA_DIR / "olist_orders_dataset.csv"
    customers_path = DATA_DIR / "olist_customers_dataset.csv"

    orders = pd.read_csv(orders_path)
    customers = pd.read_csv(customers_path)

    validated_orders, report = validate_orders(orders, customers)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    validated_orders.to_csv(
        OUTPUT_DIR / "orders_validated.csv",
        index=False
    )

    with open(
        OUTPUT_DIR / "orders_quality_report.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n=== RAPPORT DE QUALITÉ ORDERS ===")
    print("Commandes analysées :", report["total_orders"])
    print("Sans anomalie détectée :", report["valid_orders"])
    print("À examiner :", report["review_orders"])

    print("\nAnomalies par règle :")
    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")

    print("\nRésultats enregistrés dans :", OUTPUT_DIR)


if __name__ == "__main__":
    main()
