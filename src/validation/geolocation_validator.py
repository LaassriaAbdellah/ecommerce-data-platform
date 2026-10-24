"""Vectorized Geolocation validation with independent geographic indicators."""

from pathlib import Path
from time import perf_counter
import json

import numpy as np
import pandas as pd

from src.validation.common import check_required_columns, check_missing_ids
from src.validation.customers_validator import VALID_STATES
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
PREFIX = "geolocation_zip_code_prefix"
LAT = "geolocation_lat"
LNG = "geolocation_lng"
CITY = "geolocation_city"
STATE = "geolocation_state"
REQUIRED_COLUMNS = [PREFIX, LAT, LNG, CITY, STATE]


def normalize_cities(values):
    """Vectorized exploratory key; never overwrite the source city."""
    return (values.astype("string").str.casefold().str.normalize("NFKD")
            .str.replace(r"[\u0300-\u036f]", "", regex=True)
            .str.replace(r"[^a-z0-9]+", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True).str.strip())


def _apply_compressed_rules(frame, rules):
    """Run the unchanged engine on distinct masks, then expand by position.

    Nine rules yield at most 512 patterns, avoiding engine iterrows on 1M rows.
    Rule order, JSON formatting, counts and original row/index order are kept.
    """
    signature = np.zeros(len(frame), dtype=np.uint16)
    for bit, mask in enumerate(rules.values()):
        signature |= mask.fillna(False).to_numpy(dtype=np.uint16) << bit
    patterns, inverse = np.unique(signature, return_inverse=True)
    compact = pd.DataFrame(index=pd.RangeIndex(len(patterns)))
    compact_rules = {
        name: pd.Series((patterns & (1 << bit)) != 0, index=compact.index)
        for bit, name in enumerate(rules)
    }
    encoded, report = apply_quality_rules(compact, compact_rules, "geolocation")
    result = frame.copy()
    for column in ["quality_issue_count", "quality_status", "quality_issues"]:
        result[column] = encoded[column].to_numpy()[inverse]
    report.update(
        total_rows=int(len(frame)),
        valid_rows=int(np.count_nonzero(signature == 0)),
        review_rows=int(np.count_nonzero(signature != 0)),
        anomalies_by_rule={name: int(mask.fillna(False).sum())
                           for name, mask in rules.items()},
    )
    return result, report


def _summary(values):
    if values.empty:
        return {"count": 0, "min": None, "median": None, "p95": None,
                "p99": None, "max": None}
    return {"count": int(len(values)), "min": float(values.min()),
            "median": float(values.median()), "p95": float(values.quantile(.95)),
            "p99": float(values.quantile(.99)), "max": float(values.max())}


def _coverage(reference, stem, geographic):
    columns = [f"{stem}_zip_code_prefix", f"{stem}_city", f"{stem}_state"]
    check_required_columns(reference, columns)
    ref = reference[columns].copy()
    ref.columns = [PREFIX, CITY, STATE]
    ref[PREFIX] = ref[PREFIX].astype("string")
    valid_prefix = ref[PREFIX].str.fullmatch("[0-9]{5}", na=False)
    known = valid_prefix & ref[PREFIX].isin(geographic[PREFIX])
    missing_city = check_missing_ids(ref, CITY)
    valid_state = ref[STATE].isin(VALID_STATES)
    ref["city_key"] = normalize_cities(ref[CITY])
    state_pairs = geographic.loc[geographic[STATE].isin(VALID_STATES),
                                  [PREFIX, STATE]].drop_duplicates()
    city_pairs = geographic.loc[
        ~check_missing_ids(geographic, CITY), [PREFIX, "city_key"]
    ].drop_duplicates()
    observed_state = pd.MultiIndex.from_frame(ref[[PREFIX, STATE]]).isin(
        pd.MultiIndex.from_frame(state_pairs))
    observed_city = pd.MultiIndex.from_frame(ref[[PREFIX, "city_key"]]).isin(
        pd.MultiIndex.from_frame(city_pairs))
    return {
        "rows": int(len(ref)),
        "distinct_valid_prefixes": int(ref.loc[valid_prefix, PREFIX].nunique()),
        "invalid_or_missing_prefix_rows": int((~valid_prefix).sum()),
        "covered_rows": int(known.sum()),
        "absent_prefix_rows": int((valid_prefix & ~known).sum()),
        "absent_distinct_prefixes": int(ref.loc[valid_prefix & ~known, PREFIX].nunique()),
        "geolocation_prefixes_not_observed_in_reference": int(
            geographic.loc[~geographic[PREFIX].isin(ref.loc[valid_prefix, PREFIX]), PREFIX].nunique()),
        "state_comparable_rows": int((known & valid_state).sum()),
        "state_difference_rows": int((known & valid_state & ~observed_state).sum()),
        "city_comparable_rows": int((known & ~missing_city).sum()),
        "city_difference_rows": int((known & ~missing_city & ~observed_city).sum()),
    }


def validate_geolocation(geolocation: pd.DataFrame, sellers: pd.DataFrame,
                         customers: pd.DataFrame):
    """Preserve source rows; only structural errors affect quality."""
    check_required_columns(geolocation, REQUIRED_COLUMNS)
    for reference, stem in [(sellers, "seller"), (customers, "customer")]:
        check_required_columns(reference, [
            f"{stem}_zip_code_prefix", f"{stem}_city", f"{stem}_state"])
    frame = geolocation.copy()
    frame[PREFIX] = frame[PREFIX].astype("string")
    missing = {col: check_missing_ids(frame, col) for col in REQUIRED_COLUMNS}
    valid_prefix = frame[PREFIX].str.fullmatch("[0-9]{5}", na=False)
    rules = {
        "missing_geolocation_zip_code_prefix": missing[PREFIX],
        "invalid_geolocation_zip_code_prefix": ~missing[PREFIX] & ~valid_prefix,
    }
    numeric = pd.DataFrame(index=frame.index)
    valid_coordinates = pd.Series(True, index=frame.index)
    for col, lower, upper in [(LAT, -90, 90), (LNG, -180, 180)]:
        # Text conversion also rejects booleans without per-row Python maps.
        numeric[col] = pd.to_numeric(frame[col].astype("string"), errors="coerce")
        valid = (numeric[col].notna() & np.isfinite(numeric[col])
                 & numeric[col].between(lower, upper)).fillna(False)
        rules[f"missing_{col}"] = missing[col]
        rules[f"invalid_{col}"] = ~missing[col] & ~valid
        valid_coordinates &= valid
    rules["missing_geolocation_city"] = missing[CITY]
    rules["missing_geolocation_state"] = missing[STATE]
    rules["invalid_geolocation_state"] = ~missing[STATE] & ~frame[STATE].isin(VALID_STATES)
    result, report = _apply_compressed_rules(frame, rules)

    # Normalize unique city labels once, then vectorized lookup for all rows.
    labels = frame[CITY].astype("string").drop_duplicates()
    keys = pd.Series(normalize_cities(labels).to_numpy(), index=labels.to_numpy())
    geographic = frame.loc[valid_prefix, [PREFIX, CITY, STATE]].copy()
    geographic["city_key"] = geographic[CITY].astype("string").map(keys)
    cities = geographic.loc[~check_missing_ids(geographic, CITY)]
    states = geographic.loc[geographic[STATE].isin(VALID_STATES)]
    multi_cities = cities.groupby(PREFIX, observed=True)[CITY].nunique()
    multi_states = states.groupby(PREFIX, observed=True)[STATE].nunique()
    variants = cities.loc[cities[STATE].isin(VALID_STATES), [STATE, CITY, "city_key"]]
    variant_counts = variants.drop_duplicates().groupby(
        [STATE, "city_key"], observed=True)[CITY].nunique()
    valid_numeric = numeric.loc[valid_prefix & valid_coordinates].copy()
    valid_numeric[PREFIX] = frame.loc[valid_prefix & valid_coordinates, PREFIX]
    pairs = valid_numeric.drop_duplicates()
    coordinate_counts = pairs.groupby(PREFIX, observed=True).size()
    bounds = valid_numeric.groupby(PREFIX, observed=True)[[LAT, LNG]].agg(["min", "max"])
    latitude_span = bounds[(LAT, "max")] - bounds[(LAT, "min")]
    longitude_span = bounds[(LNG, "max")] - bounds[(LNG, "min")]
    report["business_indicators"] = {
        "exact_duplicate_excess_rows": int(frame[REQUIRED_COLUMNS].duplicated().sum()),
        "prefixes_multiple_coordinates": int(coordinate_counts.gt(1).sum()),
        "distinct_valid_prefix_coordinate_triples": int(len(pairs)),
        "prefixes_multiple_cities": int(multi_cities.gt(1).sum()),
        "prefixes_multiple_states": int(multi_states.gt(1).sum()),
        "city_variant_groups_same_state": int(variant_counts.gt(1).sum()),
    }
    report["coordinate_dispersion"] = {
        "latitude_span_degrees": _summary(latitude_span),
        "longitude_span_degrees": _summary(longitude_span),
    }
    report["coverage"] = {
        "sellers": _coverage(sellers, "seller", geographic),
        "customers": _coverage(customers, "customer", geographic),
    }
    report["indicator_methodology"] = {
        "reference": "Geolocation is neither official nor exhaustive; no geographic indicator affects quality.",
        "duplicates": "Excess complete source rows, before quality columns; no removal. String coordinates in CLI preserve raw spelling; caller numeric types define their own equality.",
        "coordinates": "Distinct numeric pairs per valid prefix, finite and within global inclusive bounds. No rounding; dispersion=max-min per axis in degrees, not distances.",
        "cities": "casefold, NFKD, combining accents removed, punctuation to spaces, collapsed whitespace; variants grouped by valid state. Usable fields only, not necessarily fully valid rows.",
        "coverage": "Five-digit prefixes; vectorized membership of distinct prefix/state and prefix/city-key pairs. Compare nonblank cities/recognized states on known prefixes only. Reverse coverage counts geographic prefixes absent from the reference.",
        "preservation": "No prefix uniqueness, padding, deduplication, coordinate representative or dispersion rejection threshold.",
    }
    return result, report


def main():
    started = perf_counter()
    geolocation = pd.read_csv(DATA_DIR / "olist_geolocation_dataset.csv",
        keep_default_na=False, dtype={PREFIX: "string", LAT: "string",
                                      LNG: "string", CITY: "category", STATE: "category"})
    references = {}
    for name, stem in [("sellers", "seller"), ("customers", "customer")]:
        references[name] = pd.read_csv(DATA_DIR / f"olist_{name}_dataset.csv",
            usecols=[f"{stem}_zip_code_prefix", f"{stem}_city", f"{stem}_state"],
            dtype="string")
    read_done = perf_counter()
    result, report = validate_geolocation(geolocation, references["sellers"], references["customers"])
    validation_done = perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_DIR / "geolocation_validated.csv", index=False)
    csv_done = perf_counter()
    report["execution_seconds"] = {
        "read": round(read_done - started, 3),
        "validation_including_indicators": round(validation_done - read_done, 3),
        "csv_export": round(csv_done - validation_done, 3),
    }
    with (OUTPUT_DIR / "geolocation_quality_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
