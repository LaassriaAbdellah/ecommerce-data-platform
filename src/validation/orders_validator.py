
from pathlib import Path
import json

import pandas as pd

from src.validation.common import (
    check_required_columns,
    check_missing_ids,
    check_duplicate_ids,
    check_invalid_dates,
)
from src.validation.quality_engine import apply_quality_rules

# ============================================================
# CONFIGURATION
# ============================================================

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


# ============================================================
# VALIDATION DES COMMANDES
# ============================================================

def validate_orders(
    orders: pd.DataFrame,
    customers: pd.DataFrame
):
    """
    Valider les commandes Olist.

    Retourne :
        - DataFrame avec indicateurs de qualité
        - Rapport de validation

    Les données d'entrée ne sont pas modifiées.
    """

    # --------------------------------------------------------
    # 1. Vérification des colonnes obligatoires
    # --------------------------------------------------------

    check_required_columns(orders, REQUIRED_COLUMNS)
    check_required_columns(customers, ["customer_id"])

    # Copie pour préserver les données originales
    df = orders.copy()

    # --------------------------------------------------------
    # 2. Conversion et validation des dates
    # --------------------------------------------------------

    df, invalid_date_rules = check_invalid_dates(
        df,
        DATE_COLUMNS
    )

    # --------------------------------------------------------
    # 3. Validation des identifiants
    # --------------------------------------------------------

    order_id_invalid = check_missing_ids(
        df,
        "order_id"
    )

    customer_id_invalid = check_missing_ids(
        df,
        "customer_id"
    )

    duplicate_order_id = (
        check_duplicate_ids(df, "order_id")
        & ~order_id_invalid
    )

    # --------------------------------------------------------
    # 4. Intégrité référentielle
    # --------------------------------------------------------

    customer_references = (
        customers["customer_id"].dropna()
    )

    unknown_customer = (
        ~df["customer_id"].isin(customer_references)
        & ~customer_id_invalid
    )

    # --------------------------------------------------------
    # 5. Règles de validation
    # --------------------------------------------------------

    rules = {
        # Identifiants
        "missing_order_id": order_id_invalid,
        "missing_customer_id": customer_id_invalid,
        "duplicate_order_id": duplicate_order_id,
        "unknown_customer": unknown_customer,

        # Statuts
        "invalid_order_status": (
            ~df["order_status"].isin(VALID_STATUSES)
        ),

        # Dates manquantes pour les commandes livrées
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

        # Cohérence chronologique
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

        # Dates invalides détectées par common.py
        **invalid_date_rules,
    }

    # --------------------------------------------------------
    # 6. Construction des indicateurs de qualité
    # --------------------------------------------------------

        # Appliquer le moteur de qualité générique
    validated_df, generic_report = apply_quality_rules(
        df=df,
        rules=rules,
        entity_name="orders",
    )

    # Conserver le format historique du rapport Orders
    report = {
        "total_orders": generic_report["total_rows"],
        "valid_orders": generic_report["valid_rows"],
        "review_orders": generic_report["review_rows"],
        "anomalies_by_rule": generic_report["anomalies_by_rule"],
        "duplicate_customer_ids_in_customers": int(
            customers["customer_id"].duplicated().sum()
        ),
    }

    return validated_df, report


# ============================================================
# EXECUTION DU PIPELINE
# ============================================================

def main():

    # 1. Chemins des fichiers sources
    orders_path = DATA_DIR / "olist_orders_dataset.csv"
    customers_path = DATA_DIR / "olist_customers_dataset.csv"

    # 2. Chargement des données
    orders = pd.read_csv(orders_path)
    customers = pd.read_csv(customers_path)

    # 3. Exécution de la validation
    validated_orders, report = validate_orders(
        orders,
        customers
    )

    # 4. Création du dossier de sortie
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # 5. Export des commandes validées
    validated_orders.to_csv(
        OUTPUT_DIR / "orders_validated.csv",
        index=False
    )

    # 6. Export du rapport JSON
    with open(
        OUTPUT_DIR / "orders_quality_report.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    # 7. Affichage des résultats
    print("\n=== RAPPORT DE QUALITÉ ORDERS ===")

    print(
        "Commandes analysées :",
        report["total_orders"]
    )

    print(
        "Sans anomalie détectée :",
        report["valid_orders"]
    )

    print(
        "À examiner :",
        report["review_orders"]
    )

    print("\nAnomalies par règle :")

    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")

    print(
        "\nRésultats enregistrés dans :",
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()
