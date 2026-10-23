
from pathlib import Path
import json

import pandas as pd

from src.validation.common import (
    check_required_columns,
    check_missing_ids,
    check_duplicate_ids,
)

from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"

REQUIRED_COLUMNS = [
    "customer_id",
    "customer_unique_id",
    "customer_zip_code_prefix",
    "customer_city",
    "customer_state",
]

VALID_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF",
    "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ",
    "RN", "RS", "RO", "RR", "SC", "SP",
    "SE", "TO",
}


def validate_customers(customers: pd.DataFrame):
    """Valider les clients Olist sans modifier les données d'entrée."""

    # 1. Vérifier le schéma
    check_required_columns(customers, REQUIRED_COLUMNS)

    df = customers.copy()

    # 2. Préparer les contrôles génériques
    missing_customer_id = check_missing_ids(df, "customer_id")

    zip_codes = df["customer_zip_code_prefix"].astype("string")

    # 3. Définir les règles de validation
    rules = {
        "missing_customer_id": missing_customer_id,

        "duplicate_customer_id": (
            check_duplicate_ids(df, "customer_id")
            & ~missing_customer_id
        ),

        "missing_customer_unique_id": (
            check_missing_ids(df, "customer_unique_id")
        ),

        "missing_customer_city": (
            check_missing_ids(df, "customer_city")
        ),

        "missing_customer_state": (
            check_missing_ids(df, "customer_state")
        ),

        "invalid_zip_code": (
            ~zip_codes.str.fullmatch(r"\d{5}", na=False)
        ),

        "invalid_customer_state": (
            ~df["customer_state"].isin(VALID_STATES)
        ),
    }

    # 4. Appliquer le moteur générique
    validated_df, report = apply_quality_rules(
        df=df,
        rules=rules,
        entity_name="customers",
    )

    return validated_df, report


def main():
    customers_path = DATA_DIR / "olist_customers_dataset.csv"

    # Conserver les zéros initiaux du préfixe postal
    customers = pd.read_csv(
        customers_path,
        dtype={"customer_zip_code_prefix": "string"},
    )

    validated_customers, report = validate_customers(customers)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Export des données validées
    validated_customers.to_csv(
        OUTPUT_DIR / "customers_validated.csv",
        index=False,
    )

    # Export du rapport
    with open(
        OUTPUT_DIR / "customers_quality_report.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n=== RAPPORT DE QUALITÉ CUSTOMERS ===")
    print("Clients analysés :", report["total_rows"])
    print("Sans anomalie détectée :", report["valid_rows"])
    print("À examiner :", report["review_rows"])

    print("\nAnomalies par règle :")
    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")

    print("\nRésultats enregistrés dans :", OUTPUT_DIR)


if __name__ == "__main__":
    main()
