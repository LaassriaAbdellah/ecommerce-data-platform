"""Products validation with optional metadata and separate business indicators."""

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

INTEGER_COLUMNS = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
]
PHYSICAL_COLUMNS = [
    "product_weight_g", "product_length_cm",
    "product_height_cm", "product_width_cm",
]
NUMERIC_COLUMNS = [*INTEGER_COLUMNS, *PHYSICAL_COLUMNS]
REQUIRED_COLUMNS = ["product_id", "product_category_name", *NUMERIC_COLUMNS]
TRANSLATION_COLUMNS = ["product_category_name", "product_category_name_english"]


def validate_products(products: pd.DataFrame, translations: pd.DataFrame):
    """Preserve rows/source values; optional absences are indicators, not errors.

    Present numbers must be finite and nonnegative. Descriptive lengths and
    photo counts must be integers; fractional physical measurements are allowed.
    No upper limits or translation-coverage rules alter quality_status.
    """
    check_required_columns(products, REQUIRED_COLUMNS)
    check_required_columns(translations, TRANSLATION_COLUMNS)

    missing = pd.DataFrame({
        column: check_missing_ids(products, column)
        for column in REQUIRED_COLUMNS
    }, index=products.index)
    numeric = products[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    finite = (numeric.notna() & np.isfinite(numeric)).fillna(False)
    rules = {
        "missing_product_id": missing["product_id"],
        "duplicate_product_id": (
            check_duplicate_ids(products, "product_id") & ~missing["product_id"]
        ),
    }
    numeric_summary = {}
    for column in NUMERIC_COLUMNS:
        boolean_values = products[column].map(
            lambda value: isinstance(value, (bool, np.bool_))
        ).astype(bool)
        valid = finite[column] & ~boolean_values & numeric[column].ge(0)
        if column in INTEGER_COLUMNS:
            valid &= numeric[column].where(finite[column]).mod(1).eq(0)
        valid = valid.fillna(False)
        rules[f"invalid_{column}"] = ~missing[column] & ~valid

        # Statistics exclude absent/invalid values, without defining outliers.
        values = numeric.loc[~missing[column] & valid, column]
        numeric_summary[column] = {
            "count": int(len(values)),
            "min": None if values.empty else float(values.min()),
            "median": None if values.empty else float(values.median()),
            "p99": None if values.empty else float(
                values.quantile(0.99, interpolation="linear")
            ),
            "max": None if values.empty else float(values.max()),
        }

    result, report = apply_quality_rules(products, rules, entity_name="products")
    has_translation = (
        ~check_missing_ids(translations, "product_category_name")
        & ~check_missing_ids(translations, "product_category_name_english")
    )
    translated_categories = translations.loc[
        has_translation, "product_category_name"
    ]
    untranslated = (
        ~missing["product_category_name"]
        & ~products["product_category_name"].isin(translated_categories)
    )
    weight = numeric["product_weight_g"]
    valid_weight = (
        ~missing["product_weight_g"] & ~rules["invalid_product_weight_g"]
    )
    report["business_indicators"] = {
        "missing_category_rows": int(missing["product_category_name"].sum()),
        "missing_descriptive_metadata_rows": int(
            missing[INTEGER_COLUMNS].any(axis=1).sum()
        ),
        "missing_physical_data_rows": int(
            missing[PHYSICAL_COLUMNS].any(axis=1).sum()
        ),
        "products_with_any_missing_field_rows": int(missing.any(axis=1).sum()),
        "zero_product_weight_rows": int((valid_weight & weight.eq(0)).sum()),
        "untranslated_category_rows": int(untranslated.sum()),
        "untranslated_distinct_categories": int(
            products.loc[untranslated, "product_category_name"].nunique()
        ),
    }
    report["descriptive_statistics"] = {
        "method": (
            "Per-column present, structurally valid numbers only; "
            "min, median, p99 with linear interpolation, max. No rejection threshold."
        ),
        "columns": numeric_summary,
    }
    return result, report


def main():
    products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
    translations = pd.read_csv(
        DATA_DIR / "product_category_name_translation.csv",
        usecols=TRANSLATION_COLUMNS,
    )
    validated_products, report = validate_products(products, translations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validated_products.to_csv(OUTPUT_DIR / "products_validated.csv", index=False)
    with (OUTPUT_DIR / "products_quality_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False, allow_nan=False)

    print("\n=== RAPPORT DE QUALITÉ PRODUCTS ===")
    print("Lignes analysées :", report["total_rows"])
    print("Sans anomalie détectée :", report["valid_rows"])
    print("À examiner :", report["review_rows"])
    print("\nAnomalies structurelles par règle :")
    for name, count in report["anomalies_by_rule"].items():
        print(f"  {name}: {count}")
    print("\nIndicateurs séparés (sans effet sur la qualité) :")
    for name, count in report["business_indicators"].items():
        print(f"  {name}: {count}")
    print("\nStatistiques descriptives disponibles dans le rapport JSON.")
    print("Résultats enregistrés dans :", OUTPUT_DIR)


if __name__ == "__main__":
    main()
