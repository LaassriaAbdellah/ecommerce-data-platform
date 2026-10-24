import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.validation import geolocation_validator as validator
from src.validation.quality_engine import apply_quality_rules


def make_data():
    geo = pd.DataFrame({
        validator.PREFIX: ["01234", "54321"],
        validator.LAT: [-23.5, -25.4], validator.LNG: [-46.6, -49.2],
        validator.CITY: ["sao paulo", "curitiba"], validator.STATE: ["SP", "PR"],
    })
    sellers = pd.DataFrame({
        "seller_zip_code_prefix": ["01234", "54321"],
        "seller_city": ["sao paulo", "curitiba"], "seller_state": ["SP", "PR"],
    })
    customers = sellers.rename(columns=lambda col: col.replace("seller", "customer"))
    return geo, sellers, customers


def changed(geo, column, value):
    result = geo.copy()
    result[column] = result[column].astype(object)
    result.loc[0, column] = value
    return result


def test_valid_and_leading_zero():
    geo, sellers, customers = make_data()
    result, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["valid_rows"] == 2 and report["review_rows"] == 0
    assert result[validator.PREFIX].tolist() == ["01234", "54321"]
    assert str(result[validator.PREFIX].dtype) == "string"
    assert result.quality_issue_count.eq(0).all()
    assert result.quality_issues.map(json.loads).tolist() == [[], []]
    assert report["coverage"]["sellers"]["covered_rows"] == 2


@pytest.mark.parametrize("column", validator.REQUIRED_COLUMNS)
@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing_values(column, value):
    geo, sellers, customers = make_data()
    result, report = validator.validate_geolocation(changed(geo, column, value), sellers, customers)
    assert report["anomalies_by_rule"][f"missing_{column}"] == 1
    assert result.loc[0, "quality_issue_count"] == 1


@pytest.mark.parametrize("value", ["1234", "123456", "abc12", " 12345", "12345 ", "１２３４５", 123.4, True])
def test_bad_prefix(value):
    geo, sellers, customers = make_data()
    _, report = validator.validate_geolocation(changed(geo, validator.PREFIX, value), sellers, customers)
    assert report["anomalies_by_rule"]["invalid_geolocation_zip_code_prefix"] == 1


@pytest.mark.parametrize("column", [validator.LAT, validator.LNG])
@pytest.mark.parametrize("value", ["bad", "NaN", float("inf"), -float("inf"), True, False])
def test_invalid_numeric_coordinates(column, value):
    geo, sellers, customers = make_data()
    _, report = validator.validate_geolocation(changed(geo, column, value), sellers, customers)
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1


@pytest.mark.parametrize("column,value", [
    (validator.LAT, -90.001), (validator.LAT, 90.001),
    (validator.LNG, -180.001), (validator.LNG, 180.001),
])
def test_outside_world_bounds(column, value):
    geo, sellers, customers = make_data()
    _, report = validator.validate_geolocation(changed(geo, column, value), sellers, customers)
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1


@pytest.mark.parametrize("column,value", [
    (validator.LAT, -90), (validator.LAT, 90), (validator.LAT, 0),
    (validator.LNG, -180), (validator.LNG, 180), (validator.LNG, 0),
    (validator.LAT, "45.1"), (validator.LNG, "121.1"),
])
def test_global_bounds_inclusive_and_numeric_text(column, value):
    geo, sellers, customers = make_data()
    result, report = validator.validate_geolocation(changed(geo, column, value), sellers, customers)
    assert report["review_rows"] == 0
    assert result.loc[0, column] == value


@pytest.mark.parametrize("value", ["XX", "sp", " SP"])
def test_unknown_state(value):
    geo, sellers, customers = make_data()
    _, report = validator.validate_geolocation(changed(geo, validator.STATE, value), sellers, customers)
    assert report["anomalies_by_rule"]["invalid_geolocation_state"] == 1


def test_duplicate_source_rows_are_indicators_only():
    geo, sellers, customers = make_data()
    geo = pd.concat([geo, geo.iloc[:1]], ignore_index=True)
    result, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["business_indicators"]["exact_duplicate_excess_rows"] == 1
    assert report["review_rows"] == 0 and len(result) == 3


def test_multiple_points_cities_states_and_extreme_dispersion_allowed():
    geo, sellers, customers = make_data()
    geo[validator.PREFIX] = "01234"
    geo[validator.LAT] = [-90, 90]
    geo[validator.LNG] = [-180, 180]
    _, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["review_rows"] == 0
    indicators = report["business_indicators"]
    assert indicators["prefixes_multiple_coordinates"] == 1
    assert indicators["prefixes_multiple_cities"] == 1
    assert indicators["prefixes_multiple_states"] == 1
    assert report["coordinate_dispersion"]["latitude_span_degrees"]["max"] == 180
    assert report["coordinate_dispersion"]["longitude_span_degrees"]["max"] == 360


def test_city_variants_do_not_affect_quality_or_reference_match():
    geo, sellers, customers = make_data()
    geo[validator.CITY] = ["São  Paulo", "sao paulo"]
    geo[validator.STATE] = "SP"
    geo[validator.PREFIX] = "01234"
    _, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["business_indicators"]["city_variant_groups_same_state"] == 1
    assert report["coverage"]["sellers"]["city_difference_rows"] == 0
    assert report["review_rows"] == 0


def test_bidirectional_absence_and_differences_are_not_errors():
    geo, sellers, customers = make_data()
    sellers.loc[0] = ["99999", "other", "RJ"]
    customers.loc[0] = ["01234", "other", "RJ"]
    _, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["coverage"]["sellers"]["absent_prefix_rows"] == 1
    assert report["coverage"]["sellers"]["geolocation_prefixes_not_observed_in_reference"] == 1
    assert report["coverage"]["customers"]["city_difference_rows"] == 1
    assert report["coverage"]["customers"]["state_difference_rows"] == 1
    assert report["review_rows"] == 0


def test_invalid_reference_values_not_evidence_of_disagreement():
    geo, sellers, customers = make_data()
    sellers.loc[0, ["seller_city", "seller_state"]] = None
    sellers.loc[1, "seller_zip_code_prefix"] = ""
    _, report = validator.validate_geolocation(geo, sellers, customers)
    coverage = report["coverage"]["sellers"]
    assert coverage["invalid_or_missing_prefix_rows"] == 1
    assert coverage["state_comparable_rows"] == 0
    assert coverage["city_comparable_rows"] == 0
    assert coverage["state_difference_rows"] == coverage["city_difference_rows"] == 0


def test_invalid_coordinates_excluded_from_dispersion():
    geo, sellers, customers = make_data()
    geo[validator.PREFIX] = "01234"
    geo.loc[0, validator.LAT] = 1000
    _, report = validator.validate_geolocation(geo, sellers, customers)
    assert report["coordinate_dispersion"]["latitude_span_degrees"]["max"] == 0
    assert report["business_indicators"]["prefixes_multiple_coordinates"] == 0


@pytest.mark.parametrize("column", validator.REQUIRED_COLUMNS)
def test_missing_column(column):
    geo, sellers, customers = make_data()
    with pytest.raises(ValueError, match=column):
        validator.validate_geolocation(geo.drop(columns=column), sellers, customers)


@pytest.mark.parametrize("stem", ["seller", "customer"])
@pytest.mark.parametrize("suffix", ["zip_code_prefix", "city", "state"])
def test_missing_reference_columns(stem, suffix):
    geo, sellers, customers = make_data()
    column = f"{stem}_{suffix}"
    if stem == "seller":
        sellers = sellers.drop(columns=column)
    else:
        customers = customers.drop(columns=column)
    with pytest.raises(ValueError, match=column):
        validator.validate_geolocation(geo, sellers, customers)


def test_compressed_engine_matches_original_for_all_512_patterns():
    patterns = np.arange(512, dtype=np.uint16)
    # Repeat and shuffle patterns; preserve custom duplicate index.
    positions = np.random.default_rng(42).permutation(np.tile(patterns, 2))
    source = pd.DataFrame({"source_value": positions}, index=np.arange(1024) % 37)
    rules = {f"rule_{bit}": pd.Series((positions & (1 << bit)) != 0, index=source.index)
             for bit in range(9)}
    actual, actual_report = validator._apply_compressed_rules(source, rules)
    expected, expected_report = apply_quality_rules(source, rules, "geolocation")
    pd.testing.assert_frame_equal(actual, expected)
    assert actual_report == expected_report


def test_compressed_engine_nullable_masks_match():
    source = pd.DataFrame({"x": [1, 2, 3]})
    rules = {"rule": pd.Series([True, pd.NA, False], dtype="boolean")}
    actual, report = validator._apply_compressed_rules(source, rules)
    expected, expected_report = apply_quality_rules(source, rules, "geolocation")
    pd.testing.assert_frame_equal(actual, expected)
    assert report == expected_report


def test_inputs_unchanged_and_custom_index():
    geo, sellers, customers = make_data()
    geo.index = [10, 20]
    before = [frame.copy(deep=True) for frame in [geo, sellers, customers]]
    result, _ = validator.validate_geolocation(geo, sellers, customers)
    for actual, expected in zip([geo, sellers, customers], before):
        pd.testing.assert_frame_equal(actual, expected)
    expected = geo.astype({validator.PREFIX: "string"})
    pd.testing.assert_frame_equal(result[geo.columns], expected)


def test_empty_geolocation_and_strict_json():
    geo, sellers, customers = make_data()
    result, report = validator.validate_geolocation(geo.iloc[:0], sellers, customers)
    assert result.empty and report["total_rows"] == 0
    assert report["coverage"]["sellers"]["absent_prefix_rows"] == 2
    assert report["coordinate_dispersion"]["latitude_span_degrees"]["max"] is None
    json.dumps(report, allow_nan=False)


def test_empty_references_do_not_reject_geolocation():
    geo, sellers, customers = make_data()
    _, report = validator.validate_geolocation(geo, sellers.iloc[:0], customers.iloc[:0])
    assert report["review_rows"] == 0
    assert report["coverage"]["sellers"]["geolocation_prefixes_not_observed_in_reference"] == 2


def test_main_preserves_sources_and_prefix_text(tmp_path, monkeypatch):
    geo, sellers, customers = make_data()
    source_dir = tmp_path / "data"
    source_dir.mkdir()
    for frame, name in [(geo, "geolocation"), (sellers, "sellers"), (customers, "customers")]:
        frame.to_csv(source_dir / f"olist_{name}_dataset.csv", index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.iterdir()}
    monkeypatch.setattr(validator, "DATA_DIR", source_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", source_dir / "processed")
    validator.main()
    result = pd.read_csv(source_dir / "processed/geolocation_validated.csv",
                         dtype={validator.PREFIX: "string"})
    assert result[validator.PREFIX].tolist() == ["01234", "54321"]
    assert result.quality_status.eq("valid").all()
    report = json.loads((source_dir / "processed/geolocation_quality_report.json").read_text(encoding="utf-8"))
    assert report["valid_rows"] == 2
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
