import hashlib
import json

import pandas as pd
import pytest

from src.validation import sellers_validator as validator


def make_data():
    sellers = pd.DataFrame({
        "seller_id": ["S1", "S2"],
        "seller_zip_code_prefix": ["01234", "54321"],
        "seller_city": ["sao paulo", "curitiba"],
        "seller_state": ["SP", "PR"],
    })
    items = pd.DataFrame({"seller_id": ["S1", "S1", "S2"]})
    customers = pd.DataFrame({
        "customer_zip_code_prefix": ["01234", "54321"],
        "customer_city": ["sao paulo", "curitiba"],
        "customer_state": ["SP", "PR"],
    })
    return sellers, items, customers


def test_valid_and_postal_text():
    sellers, items, customers = make_data()
    result, report = validator.validate_sellers(sellers, items, customers)
    assert report["valid_rows"] == 2 and report["review_rows"] == 0
    assert result.seller_zip_code_prefix.tolist() == ["01234", "54321"]
    assert str(result.seller_zip_code_prefix.dtype) == "string"
    assert result.quality_issue_count.eq(0).all()
    assert result.quality_issues.map(json.loads).tolist() == [[], []]
    assert report["inter_table_checks"]["order_items_seller_references"]["status"] == "pass"


@pytest.mark.parametrize("column,rule", [
    ("seller_id", "missing_seller_id"),
    ("seller_zip_code_prefix", "missing_seller_zip_code_prefix"),
    ("seller_city", "missing_seller_city"),
    ("seller_state", "missing_seller_state"),
])
@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing(column, rule, value):
    sellers, items, customers = make_data()
    sellers.loc[0, column] = value
    result, report = validator.validate_sellers(sellers, items, customers)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"][rule] == 1
    assert result.loc[0, "quality_issue_count"] == 1


def test_duplicate_ids_all_occurrences():
    sellers, items, customers = make_data()
    sellers.loc[1, "seller_id"] = "S1"
    _, report = validator.validate_sellers(sellers, items, customers)
    assert report["anomalies_by_rule"]["duplicate_seller_id"] == 2


def test_missing_ids_not_duplicate():
    sellers, items, customers = make_data()
    sellers["seller_id"] = None
    _, report = validator.validate_sellers(sellers, items, customers)
    assert report["anomalies_by_rule"]["duplicate_seller_id"] == 0


@pytest.mark.parametrize("value", ["1234", "123456", "ab123", "12.34", " 12345", "12345 ", "１２３４５", "١٢٣٤٥", -1234, 12345.0, True])
def test_bad_postal(value):
    sellers, items, customers = make_data()
    sellers["seller_zip_code_prefix"] = sellers.seller_zip_code_prefix.astype(object)
    sellers.loc[0, "seller_zip_code_prefix"] = value
    _, report = validator.validate_sellers(sellers, items, customers)
    assert report["anomalies_by_rule"]["invalid_seller_zip_code_prefix"] == 1


@pytest.mark.parametrize("value", ["01234", "00000", "99999", 12345])
def test_postal_format_without_arbitrary_ranges(value):
    sellers, items, customers = make_data()
    sellers["seller_zip_code_prefix"] = sellers.seller_zip_code_prefix.astype(object)
    sellers.loc[0, "seller_zip_code_prefix"] = value
    result, report = validator.validate_sellers(sellers, items, customers)
    assert report["review_rows"] == 0
    assert result.loc[0, "seller_zip_code_prefix"] == str(value)


@pytest.mark.parametrize("state", ["XX", "sp", " SP", "BR"])
def test_unknown_state(state):
    sellers, items, customers = make_data()
    sellers.loc[0, "seller_state"] = state
    _, report = validator.validate_sellers(sellers, items, customers)
    assert report["anomalies_by_rule"]["invalid_seller_state"] == 1


@pytest.mark.parametrize("state", sorted(validator.VALID_STATES))
def test_all_27_states_accepted(state):
    sellers, items, customers = make_data()
    sellers.loc[0, "seller_state"] = state
    _, report = validator.validate_sellers(sellers, items, customers)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", validator.REQUIRED_COLUMNS)
def test_missing_seller_column(column):
    sellers, items, customers = make_data()
    with pytest.raises(ValueError, match=column):
        validator.validate_sellers(sellers.drop(columns=column), items, customers)


@pytest.mark.parametrize("table,column", [
    ("items", "seller_id"),
    *[("customers", col) for col in validator.CUSTOMER_COLUMNS],
])
def test_missing_reference_column(table, column):
    sellers, items, customers = make_data()
    if table == "items":
        items = items.drop(columns=column)
    else:
        customers = customers.drop(columns=column)
    with pytest.raises(ValueError, match=column):
        validator.validate_sellers(sellers, items, customers)


def test_orphan_references_do_not_change_seller_quality():
    sellers, _, customers = make_data()
    items = pd.DataFrame({"seller_id": ["S1", "UNKNOWN", "UNKNOWN", None, " "]})
    result, report = validator.validate_sellers(sellers, items, customers)
    check = report["inter_table_checks"]["order_items_seller_references"]
    assert check == {
        "status": "fail", "item_rows": 5, "missing_seller_id_rows": 2,
        "unknown_seller_id_rows": 2, "unknown_distinct_seller_ids": 1,
        "unreferenced_seller_rows": 1,
    }
    assert report["review_rows"] == 0 and result.quality_status.eq("valid").all()


def test_missing_seller_not_matched_to_missing_item():
    sellers, _, customers = make_data()
    sellers.loc[0, "seller_id"] = None
    _, report = validator.validate_sellers(sellers, pd.DataFrame({"seller_id": [None]}), customers)
    check = report["inter_table_checks"]["order_items_seller_references"]
    assert check["missing_seller_id_rows"] == 1 and check["status"] == "fail"


def test_city_variants_and_multicity_prefix_are_indicators():
    sellers, items, customers = make_data()
    sellers.loc[1] = ["S2", "01234", "São  Paulo", "SP"]
    result, report = validator.validate_sellers(sellers, items, customers)
    indicators = report["business_indicators"]
    assert indicators["city_variant_groups"] == 1
    assert indicators["city_variant_rows"] == 2
    assert indicators["prefixes_multiple_cities"] == 1
    assert indicators["customer_city_difference_rows"] == 0
    assert result.quality_status.eq("valid").all()


def test_multistate_and_geographic_divergence_only_indicators():
    sellers, items, customers = make_data()
    sellers.loc[1] = ["S2", "01234", "other city", "RJ"]
    _, report = validator.validate_sellers(sellers, items, customers)
    indicators = report["business_indicators"]
    assert indicators["prefixes_multiple_states"] == 1
    assert indicators["multiple_state_prefix_rows"] == 2
    assert indicators["customer_state_difference_rows"] == 1
    assert indicators["customer_city_difference_rows"] == 1
    assert report["review_rows"] == 0


def test_unseen_prefix_excluded_from_differences():
    sellers, items, customers = make_data()
    sellers.loc[1, "seller_zip_code_prefix"] = "99999"
    _, report = validator.validate_sellers(sellers, items, customers)
    indicators = report["business_indicators"]
    assert indicators["prefix_not_observed_in_customers_rows"] == 1
    assert indicators["customer_state_difference_rows"] == 0
    assert indicators["customer_city_difference_rows"] == 0
    assert indicators["customer_state_comparable_rows"] == 1


def test_empty_customer_values_not_geographic_evidence():
    sellers, items, customers = make_data()
    customers.loc[0, ["customer_city", "customer_state"]] = None
    _, report = validator.validate_sellers(sellers, items, customers)
    indicators = report["business_indicators"]
    assert indicators["customer_state_comparable_rows"] == 1
    assert indicators["customer_city_comparable_rows"] == 1
    assert indicators["customer_state_difference_rows"] == 0


def test_customer_duplicates_do_not_multiply_rows():
    sellers, items, customers = make_data()
    customers = pd.concat([customers, customers], ignore_index=True)
    result, report = validator.validate_sellers(sellers, items, customers)
    assert len(result) == 2 and report["review_rows"] == 0


def test_nonmutation_and_custom_index():
    sellers, items, customers = make_data()
    sellers.index = [10, 20]
    originals = [frame.copy(deep=True) for frame in [sellers, items, customers]]
    result, _ = validator.validate_sellers(sellers, items, customers)
    for actual, expected in zip([sellers, items, customers], originals):
        pd.testing.assert_frame_equal(actual, expected)
    assert result.index.tolist() == [10, 20]
    pd.testing.assert_frame_equal(result.drop(columns=[
        "quality_issue_count", "quality_status", "quality_issues"
    ]).astype({"seller_zip_code_prefix": "string"}),
        sellers.astype({"seller_zip_code_prefix": "string"}))


def test_empty_tables():
    sellers, items, customers = make_data()
    result, report = validator.validate_sellers(sellers.iloc[:0], items.iloc[:0], customers.iloc[:0])
    assert result.empty and report["total_rows"] == 0
    assert not any(report["business_indicators"].values())
    json.dumps(report, allow_nan=False)


def test_main_exports_preserving_sources_and_leading_zeros(tmp_path, monkeypatch):
    sellers, items, customers = make_data()
    source_dir = tmp_path / "data"
    source_dir.mkdir()
    for frame, filename in [
        (sellers, "olist_sellers_dataset.csv"),
        (items, "olist_order_items_dataset.csv"),
        (customers, "olist_customers_dataset.csv"),
    ]:
        frame.to_csv(source_dir / filename, index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.iterdir()}
    monkeypatch.setattr(validator, "DATA_DIR", source_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", source_dir / "processed")
    validator.main()
    exported = pd.read_csv(source_dir / "processed/sellers_validated.csv", dtype="string")
    assert exported.seller_zip_code_prefix.tolist() == ["01234", "54321"]
    report = json.loads((source_dir / "processed/sellers_quality_report.json").read_text(encoding="utf-8"))
    assert report["valid_rows"] == 2
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
