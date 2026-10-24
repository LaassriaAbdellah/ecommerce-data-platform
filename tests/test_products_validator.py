import hashlib
import json

import pandas as pd
import pytest

from src.validation import products_validator as validator
from src.validation.products_validator import (
    INTEGER_COLUMNS,
    NUMERIC_COLUMNS,
    PHYSICAL_COLUMNS,
    REQUIRED_COLUMNS,
    TRANSLATION_COLUMNS,
    validate_products,
)


def make_data():
    products = pd.DataFrame({
        "product_id": ["P1", "P2"],
        "product_category_name": ["cat_a", "cat_b"],
        "product_name_lenght": [20, 30],
        "product_description_lenght": [100, 200],
        "product_photos_qty": [1, 2],
        "product_weight_g": [1000, 500],
        "product_length_cm": [30, 20],
        "product_height_cm": [10, 5],
        "product_width_cm": [20, 15],
    })
    translations = pd.DataFrame({
        "product_category_name": ["cat_a", "cat_b"],
        "product_category_name_english": ["category_a", "category_b"],
    })
    return products, translations


def with_value(products, column, value):
    result = products.copy()
    result[column] = result[column].astype(object)
    result.loc[0, column] = value
    return result


def test_valid_products():
    products, translations = make_data()
    result, report = validate_products(products, translations)
    assert report["entity"] == "products"
    assert report["total_rows"] == report["valid_rows"] == 2
    assert report["review_rows"] == 0
    assert result["quality_status"].eq("valid").all()
    assert result["quality_issue_count"].eq(0).all()
    assert result["quality_issues"].map(json.loads).tolist() == [[], []]
    assert not any(report["business_indicators"].values())
    assert "product_name_lenght" in result
    assert "product_description_lenght" in result
    assert "product_name_length" not in result


@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing_product_id(value):
    products, translations = make_data()
    _, report = validate_products(with_value(products, "product_id", value), translations)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"]["missing_product_id"] == 1
    assert report["business_indicators"]["products_with_any_missing_field_rows"] == 1


def test_duplicate_product_id():
    products, translations = make_data()
    products["product_id"] = ["P1", "P1"]
    result, report = validate_products(products, translations)
    assert report["review_rows"] == 2
    assert report["anomalies_by_rule"]["duplicate_product_id"] == 2
    assert result["quality_issues"].map(json.loads).tolist() == [
        ["duplicate_product_id"], ["duplicate_product_id"]
    ]


def test_missing_ids_not_also_counted_as_duplicates():
    products, translations = make_data()
    products["product_id"] = [None, None]
    _, report = validate_products(products, translations)
    assert report["anomalies_by_rule"]["missing_product_id"] == 2
    assert report["anomalies_by_rule"]["duplicate_product_id"] == 0


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
def test_missing_required_column(column):
    products, translations = make_data()
    with pytest.raises(ValueError, match=column):
        validate_products(products.drop(columns=[column]), translations)


@pytest.mark.parametrize("column", TRANSLATION_COLUMNS)
def test_missing_translation_column(column):
    products, translations = make_data()
    with pytest.raises(ValueError, match=column):
        validate_products(products, translations.drop(columns=[column]))


@pytest.mark.parametrize("column", NUMERIC_COLUMNS)
@pytest.mark.parametrize("value", [
    -1, "bad", float("inf"), -float("inf"), True, False
])
def test_invalid_present_number(column, value):
    products, translations = make_data()
    result, report = validate_products(with_value(products, column, value), translations)
    assert report["review_rows"] == 1
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1
    assert result.loc[0, "quality_status"] == "review"
    assert report["business_indicators"]["products_with_any_missing_field_rows"] == 0


@pytest.mark.parametrize("column", NUMERIC_COLUMNS)
@pytest.mark.parametrize("value", [None, pd.NA, float("nan"), "", "   "])
def test_optional_numeric_value_missing_is_allowed(column, value):
    products, translations = make_data()
    result, report = validate_products(with_value(products, column, value), translations)
    assert report["review_rows"] == 0
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 0
    assert report["business_indicators"]["products_with_any_missing_field_rows"] == 1
    assert result["quality_issue_count"].eq(0).all()
    assert report["descriptive_statistics"]["columns"][column]["count"] == 1


@pytest.mark.parametrize("column", INTEGER_COLUMNS)
def test_fractional_counter_is_invalid(column):
    products, translations = make_data()
    _, report = validate_products(with_value(products, column, 1.5), translations)
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1
    assert report["review_rows"] == 1


@pytest.mark.parametrize("column", PHYSICAL_COLUMNS)
def test_fractional_physical_measurement_is_allowed(column):
    products, translations = make_data()
    _, report = validate_products(with_value(products, column, 1.5), translations)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", NUMERIC_COLUMNS)
def test_numeric_zero_is_allowed(column):
    products, translations = make_data()
    result, report = validate_products(with_value(products, column, 0), translations)
    assert report["review_rows"] == 0
    assert result["quality_issue_count"].eq(0).all()
    expected_weight_zeros = 1 if column == "product_weight_g" else 0
    assert report["business_indicators"]["zero_product_weight_rows"] == expected_weight_zeros


@pytest.mark.parametrize("column", NUMERIC_COLUMNS)
def test_numeric_text_is_accepted_without_modifying_value(column):
    products, translations = make_data()
    result, report = validate_products(with_value(products, column, "12"), translations)
    assert report["review_rows"] == 0
    assert result.loc[0, column] == "12"


@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing_category_is_only_indicator(value):
    products, translations = make_data()
    result, report = validate_products(
        with_value(products, "product_category_name", value), translations
    )
    indicators = report["business_indicators"]
    assert report["review_rows"] == 0
    assert indicators["missing_category_rows"] == 1
    assert indicators["untranslated_category_rows"] == 0
    assert indicators["missing_descriptive_metadata_rows"] == 0
    assert result.loc[0, "quality_issue_count"] == 0


def test_unknown_category_is_only_indicator():
    products, translations = make_data()
    products["product_category_name"] = ["new_category", "new_category"]
    result, report = validate_products(products, translations)
    assert report["review_rows"] == 0
    assert report["business_indicators"]["untranslated_category_rows"] == 2
    assert report["business_indicators"]["untranslated_distinct_categories"] == 1
    assert result["quality_issues"].map(json.loads).tolist() == [[], []]


def test_blank_english_translation_counts_as_untranslated():
    products, translations = make_data()
    translations.loc[0, "product_category_name_english"] = "   "
    _, report = validate_products(products, translations)
    assert report["review_rows"] == 0
    assert report["business_indicators"]["untranslated_category_rows"] == 1


def test_duplicate_translation_rows_do_not_multiply_products():
    products, translations = make_data()
    translations = pd.concat([translations, translations.iloc[[0]]], ignore_index=True)
    result, report = validate_products(products, translations)
    assert len(result) == report["total_rows"] == 2
    assert report["business_indicators"]["untranslated_category_rows"] == 0


def test_empty_translation_table_only_affects_indicator():
    products, translations = make_data()
    _, report = validate_products(products, translations.iloc[:0])
    assert report["review_rows"] == 0
    assert report["business_indicators"]["untranslated_category_rows"] == 2


def test_missing_indicators_do_not_double_count_products():
    products, translations = make_data()
    for column in ["product_category_name", *NUMERIC_COLUMNS]:
        products[column] = products[column].astype(object)
        products.loc[0, column] = None
    products.loc[1, "product_width_cm"] = None
    result, report = validate_products(products, translations)
    indicators = report["business_indicators"]
    assert indicators["missing_category_rows"] == 1
    assert indicators["missing_descriptive_metadata_rows"] == 1
    assert indicators["missing_physical_data_rows"] == 2
    assert indicators["products_with_any_missing_field_rows"] == 2
    assert report["review_rows"] == 0
    assert result["quality_issues"].map(json.loads).tolist() == [[], []]


def test_large_values_have_no_arbitrary_upper_limit():
    products, translations = make_data()
    for column in NUMERIC_COLUMNS:
        products[column] = [1_000_000_000, 2_000_000_000]
    result, report = validate_products(products, translations)
    assert report["review_rows"] == 0
    assert result["quality_issue_count"].eq(0).all()
    summary = report["descriptive_statistics"]["columns"]["product_weight_g"]
    assert summary["max"] == 2_000_000_000
    assert summary["p99"] == pytest.approx(1_990_000_000)


def test_summary_excludes_invalid_and_missing_numbers():
    products, translations = make_data()
    products = with_value(products, "product_weight_g", -100)
    _, report = validate_products(products, translations)
    summary = report["descriptive_statistics"]["columns"]["product_weight_g"]
    assert summary == {
        "count": 1, "min": 500, "median": 500, "p99": 500, "max": 500,
    }


def test_all_missing_optional_values_have_json_null_statistics():
    products, translations = make_data()
    for column in NUMERIC_COLUMNS:
        products[column] = None
    _, report = validate_products(products, translations)
    assert report["review_rows"] == 0
    for summary in report["descriptive_statistics"]["columns"].values():
        assert summary == {
            "count": 0, "min": None, "median": None, "p99": None, "max": None,
        }
    json.dumps(report, allow_nan=False)


def test_multiple_structural_issues_count_one_row():
    products, translations = make_data()
    products.loc[0, "product_photos_qty"] = -1
    products.loc[0, "product_weight_g"] = -1
    result, report = validate_products(products, translations)
    assert report["review_rows"] == report["valid_rows"] == 1
    issues = json.loads(result.loc[0, "quality_issues"])
    assert set(issues) == {"invalid_product_photos_qty", "invalid_product_weight_g"}
    assert len(issues) == result.loc[0, "quality_issue_count"] == 2


def test_inputs_and_index_preserved():
    products, translations = make_data()
    products.index = [10, 20]
    original_products = products.copy(deep=True)
    original_translations = translations.copy(deep=True)
    result, _ = validate_products(products, translations)
    pd.testing.assert_frame_equal(products, original_products)
    pd.testing.assert_frame_equal(translations, original_translations)
    assert result.index.tolist() == [10, 20]


def test_empty_products():
    products, translations = make_data()
    result, report = validate_products(products.iloc[:0], translations)
    assert result.empty
    assert report["total_rows"] == report["valid_rows"] == report["review_rows"] == 0
    assert all(value == 0 for value in report["business_indicators"].values())
    json.dumps(report, allow_nan=False)


def test_main_exports_without_modifying_sources(tmp_path, monkeypatch):
    products, translations = make_data()
    products.loc[0, "product_weight_g"] = 0
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    products_path = data_dir / "olist_products_dataset.csv"
    translation_path = data_dir / "product_category_name_translation.csv"
    products.to_csv(products_path, index=False)
    translations.to_csv(translation_path, index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (products_path, translation_path)}
    monkeypatch.setattr(validator, "DATA_DIR", data_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", data_dir / "processed")

    validator.main()

    report = json.loads((data_dir / "processed/products_quality_report.json").read_text(
        encoding="utf-8"
    ))
    saved = pd.read_csv(data_dir / "processed/products_validated.csv")
    assert report["total_rows"] == report["valid_rows"] == len(saved) == 2
    assert report["review_rows"] == 0
    assert report["business_indicators"]["zero_product_weight_rows"] == 1
    assert saved["quality_status"].eq("valid").all()
    assert "business_indicators" not in report["anomalies_by_rule"]
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
