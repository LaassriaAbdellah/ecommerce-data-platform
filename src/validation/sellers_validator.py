"""Sellers quality rules, geographic indicators and separate Item references."""

from pathlib import Path
import json
import re
import unicodedata

import pandas as pd

from src.validation.common import (
    check_required_columns, check_missing_ids, check_duplicate_ids,
)
from src.validation.customers_validator import VALID_STATES
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
REQUIRED_COLUMNS = [
    "seller_id", "seller_zip_code_prefix", "seller_city", "seller_state",
]
CUSTOMER_COLUMNS = [
    "customer_zip_code_prefix", "customer_city", "customer_state",
]


def normalize_city(value):
    """Exploratory key only; never replace a source city."""
    if pd.isna(value):
        return None
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def validate_sellers(sellers: pd.DataFrame, items: pd.DataFrame,
                     customers: pd.DataFrame):
    """Keep Sellers quality independent of geography and orphan Item references.

    Postal codes are represented as string without padding or trimming.
    A zero lost before this call cannot be recovered automatically.
    Missing values are not counted again as invalid format/state.
    """
    check_required_columns(sellers, REQUIRED_COLUMNS)
    check_required_columns(items, ["seller_id"])
    check_required_columns(customers, CUSTOMER_COLUMNS)
    df = sellers.copy()
    df["seller_zip_code_prefix"] = df["seller_zip_code_prefix"].astype("string")
    missing = {col: check_missing_ids(df, col) for col in REQUIRED_COLUMNS}
    valid_zip = df.seller_zip_code_prefix.str.fullmatch("[0-9]{5}", na=False)
    valid_state = df.seller_state.isin(VALID_STATES)
    rules = {
        "missing_seller_id": missing["seller_id"],
        "duplicate_seller_id": check_duplicate_ids(df, "seller_id") & ~missing["seller_id"],
        "missing_seller_zip_code_prefix": missing["seller_zip_code_prefix"],
        "invalid_seller_zip_code_prefix": ~missing["seller_zip_code_prefix"] & ~valid_zip,
        "missing_seller_city": missing["seller_city"],
        "missing_seller_state": missing["seller_state"],
        "invalid_seller_state": ~missing["seller_state"] & ~valid_state,
    }
    result, report = apply_quality_rules(df, rules, entity_name="sellers")

    # Missing references cannot be assigned to any existing Seller row.
    missing_item_id = check_missing_ids(items, "seller_id")
    known_ids = df.loc[~missing["seller_id"], "seller_id"]
    unknown = ~missing_item_id & ~items.seller_id.isin(known_ids)
    report["inter_table_checks"] = {
        "order_items_seller_references": {
            "status": "fail" if (missing_item_id | unknown).any() else "pass",
            "item_rows": int(len(items)),
            "missing_seller_id_rows": int(missing_item_id.sum()),
            "unknown_seller_id_rows": int(unknown.sum()),
            "unknown_distinct_seller_ids": int(items.loc[unknown, "seller_id"].nunique()),
            "unreferenced_seller_rows": int((
                ~missing["seller_id"] & ~df.seller_id.isin(items.loc[~missing_item_id, "seller_id"])
            ).sum()),
        },
    }

    # Indicators use usable fields, not necessarily fully valid Seller rows.
    geo = df.loc[~missing["seller_city"] & valid_state].copy()
    geo["city_key"] = geo.seller_city.map(normalize_city)
    variant_counts = geo.groupby(["seller_state", "city_key"]).seller_city.nunique()
    variant_keys = variant_counts[variant_counts.gt(1)].index
    variant_rows = pd.MultiIndex.from_frame(
        geo[["seller_state", "city_key"]]
    ).isin(variant_keys)
    prefix_geo = df.loc[valid_zip].copy()
    states_per_prefix = prefix_geo.loc[
        prefix_geo.seller_state.isin(VALID_STATES)
    ].groupby("seller_zip_code_prefix").seller_state.nunique()
    cities_per_prefix = prefix_geo.loc[
        ~check_missing_ids(prefix_geo, "seller_city")
    ].groupby("seller_zip_code_prefix").seller_city.nunique()
    multistate = states_per_prefix[states_per_prefix.gt(1)].index
    multicity = cities_per_prefix[cities_per_prefix.gt(1)].index

    customer_geo = customers.copy()
    customer_geo["customer_zip_code_prefix"] = customer_geo[
        "customer_zip_code_prefix"
    ].astype("string")
    usable_customer_zip = customer_geo.customer_zip_code_prefix.str.fullmatch(
        "[0-9]{5}", na=False
    )
    customer_geo = customer_geo.loc[usable_customer_zip].copy()
    customer_geo["city_key"] = customer_geo.customer_city.map(normalize_city)
    customer_prefixes = set(customer_geo.customer_zip_code_prefix)
    state_sets = customer_geo.loc[
        customer_geo.customer_state.isin(VALID_STATES)
    ].groupby("customer_zip_code_prefix").customer_state.agg(set).to_dict()
    city_sets = customer_geo.loc[
        ~check_missing_ids(customer_geo, "customer_city")
    ].groupby("customer_zip_code_prefix").city_key.agg(set).to_dict()
    state_comparable = city_comparable = state_differences = city_differences = 0
    for prefix, city, state in df[REQUIRED_COLUMNS[1:]].itertuples(index=False, name=None):
        if pd.isna(prefix) or not re.fullmatch("[0-9]{5}", prefix):
            continue
        if prefix in state_sets and state in VALID_STATES:
            state_comparable += 1
            state_differences += state not in state_sets[prefix]
        key = normalize_city(city)
        if prefix in city_sets and key:
            city_comparable += 1
            city_differences += key not in city_sets[prefix]
    report["business_indicators"] = {
        "city_variant_groups": int(len(variant_keys)),
        "city_variant_rows": int(variant_rows.sum()),
        "prefixes_multiple_states": int(len(multistate)),
        "multiple_state_prefix_rows": int(prefix_geo.seller_zip_code_prefix.isin(multistate).sum()),
        "prefixes_multiple_cities": int(len(multicity)),
        "multiple_city_prefix_rows": int(prefix_geo.seller_zip_code_prefix.isin(multicity).sum()),
        "prefix_not_observed_in_customers_rows": int((
            valid_zip & ~df.seller_zip_code_prefix.isin(customer_prefixes)
        ).sum()),
        "customer_state_comparable_rows": int(state_comparable),
        "customer_state_difference_rows": int(state_differences),
        "customer_city_comparable_rows": int(city_comparable),
        "customer_city_difference_rows": int(city_differences),
    }
    report["indicator_methodology"] = {
        "reference": "Customers is an observed sample, not an official geographic reference.",
        "city_key": "casefold; NFKD; remove combining accents; punctuation to spaces; collapse spaces.",
        "variants": "Distinct source cities per (valid state, normalized city); rows include every spelling.",
        "eligibility": "Five ASCII postal digits; nonblank cities and recognized states for their respective comparisons. Customer groups with no usable compared value excluded.",
        "counts": "Seller rows unless named groups/prefixes. Groups overlap; do not sum. No geographic indicator affects quality.",
        "references": "Item missing/unknown references reported separately; no error assigned to an existing Seller.",
    }
    return result, report


def main():
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv",
                          dtype={"seller_zip_code_prefix": "string"})
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv", usecols=["seller_id"])
    customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv",
                            usecols=CUSTOMER_COLUMNS,
                            dtype={"customer_zip_code_prefix": "string"})
    result, report = validate_sellers(sellers, items, customers)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_DIR / "sellers_validated.csv", index=False)
    with (OUTPUT_DIR / "sellers_quality_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
