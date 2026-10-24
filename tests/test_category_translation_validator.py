import hashlib
import json

import pandas as pd
import pytest

from src.validation import category_translation_validator as validator

PT, EN = validator.PT, validator.EN


def make_data():
    translations = pd.DataFrame({PT: ["cat_a", "cat_b"], EN: ["category_a", "category_b"]})
    products = pd.DataFrame({PT: ["cat_a", "cat_b", "cat_b"]})
    return translations, products


def test_valid():
    translations, products = make_data()
    result, report = validator.validate_category_translation(translations, products)
    assert report["entity"] == "category_translation"
    assert report["valid_rows"] == 2 and report["review_rows"] == 0
    assert result.quality_issue_count.eq(0).all()
    assert result.quality_issues.map(json.loads).tolist() == [[], []]


@pytest.mark.parametrize("column", [PT, EN])
def test_missing_columns(column):
    translations, products = make_data()
    with pytest.raises(ValueError, match=column):
        validator.validate_category_translation(translations.drop(columns=column), products)


def test_missing_products_category_column():
    translations, products = make_data()
    with pytest.raises(ValueError, match=PT):
        validator.validate_category_translation(translations, products.drop(columns=PT))


@pytest.mark.parametrize("column", [PT, EN])
@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_missing_fields(column, value):
    translations, products = make_data()
    translations.loc[0, column] = value
    result, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"][f"missing_{column}"] == 1
    assert result.loc[0, "quality_issue_count"] == 1


def test_exact_duplicate_category_counts_every_occurrence_once():
    translations, products = make_data()
    translations = pd.concat([translations, translations.iloc[:1]], ignore_index=True)
    result, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"]["duplicate_product_category_name"] == 2
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 0
    assert result.quality_issue_count.tolist() == [1, 0, 1]
    assert report["review_rows"] == 2


def test_conflicting_translations_exclude_duplicate_rule():
    translations, products = make_data()
    translations[PT] = "cat_a"
    result, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 2
    assert report["anomalies_by_rule"]["duplicate_product_category_name"] == 0
    assert result.quality_issue_count.eq(1).all()
    assert result.quality_issues.map(json.loads).tolist() == [
        ["conflicting_category_translation"], ["conflicting_category_translation"]]
    assert report["business_indicators"]["products_on_conflicting_categories_rows"] == 1


def test_conflicting_group_with_repeated_pair_still_one_key_issue():
    translations, products = make_data()
    translations[PT] = "cat_a"
    translations = pd.concat([translations, translations.iloc[:1]], ignore_index=True)
    result, report = validator.validate_category_translation(translations, products)
    assert report["review_rows"] == 3
    assert result.quality_issue_count.eq(1).all()
    assert report["anomalies_by_rule"]["duplicate_product_category_name"] == 0


def test_missing_english_independent_of_conflicting_key_issue():
    translations, products = make_data()
    translations[PT] = "cat_a"
    translations = pd.concat([translations, pd.DataFrame({PT:["cat_a"], EN:[None]})], ignore_index=True)
    result, report = validator.validate_category_translation(translations, products)
    assert result.quality_issue_count.tolist() == [1, 1, 2]
    assert report["review_rows"] == 3
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 3
    assert report["anomalies_by_rule"]["missing_product_category_name_english"] == 1


def test_missing_english_not_a_second_distinct_translation():
    translations, products = make_data()
    translations[PT] = "cat_a"
    translations.loc[1, EN] = " "
    result, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 0
    assert report["anomalies_by_rule"]["duplicate_product_category_name"] == 2
    assert result.quality_issue_count.tolist() == [1, 2]


def test_missing_keys_never_become_duplicates():
    translations, products = make_data()
    translations[PT] = None
    _, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"]["missing_product_category_name"] == 2
    assert report["anomalies_by_rule"]["duplicate_product_category_name"] == 0
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 0


def test_shared_english_allowed_and_listed():
    translations, products = make_data()
    translations[EN] = "same_english"
    _, report = validator.validate_category_translation(translations, products)
    assert report["review_rows"] == 0
    indicators = report["business_indicators"]
    assert indicators["shared_english_distinct_labels"] == 1
    assert indicators["shared_english_categories"] == {"same_english":["cat_a", "cat_b"]}


def test_untranslated_products_and_missing_categories_separated():
    translations, _ = make_data()
    products = pd.DataFrame({PT:["pc_gamer","pc_gamer","other", None,"","   ","cat_a"]})
    _, report = validator.validate_category_translation(translations, products)
    indicators = report["business_indicators"]
    assert indicators["untranslated_products_by_category"] == {"pc_gamer":2,"other":1}
    assert indicators["untranslated_product_rows"] == 3
    assert indicators["untranslated_distinct_categories"] == 2
    assert indicators["products_without_category_rows"] == 3
    assert report["review_rows"] == 0


def test_missing_english_is_not_product_coverage():
    translations, products = make_data()
    translations.loc[1, EN] = None
    _, report = validator.validate_category_translation(translations, products)
    assert report["business_indicators"]["untranslated_products_by_category"] == {"cat_b":2}


def test_unused_translation_only_indicator():
    translations, products = make_data()
    products = products.iloc[:1]
    _, report = validator.validate_category_translation(translations, products)
    assert report["business_indicators"]["unused_translated_categories"] == ["cat_b"]
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", [PT, EN])
def test_variants_only_indicators_and_source_unchanged(column):
    translations, products = make_data()
    translations[column] = ["Ábc def", "abc_def"]
    result, report = validator.validate_category_translation(translations, products)
    assert report["writing_indicators"][column]["variant_groups"] == 1
    assert report["review_rows"] == 0
    pd.testing.assert_frame_equal(result[translations.columns], translations)


def test_no_normalization_before_conflict_detection():
    translations, products = make_data()
    translations[PT] = "cat_a"
    translations[EN] = ["english", " English "]
    _, report = validator.validate_category_translation(translations, products)
    assert report["anomalies_by_rule"]["conflicting_category_translation"] == 2


def test_inputs_and_custom_index_preserved():
    translations, products = make_data()
    translations.index = [10, 20]
    originals = [translations.copy(deep=True), products.copy(deep=True)]
    result, _ = validator.validate_category_translation(translations, products)
    pd.testing.assert_frame_equal(translations, originals[0])
    pd.testing.assert_frame_equal(products, originals[1])
    pd.testing.assert_frame_equal(result[translations.columns], translations)


def test_empty_translation_table_and_strict_json():
    translations, products = make_data()
    result, report = validator.validate_category_translation(translations.iloc[:0], products)
    assert result.empty and report["total_rows"] == 0
    assert report["business_indicators"]["untranslated_product_rows"] == 3
    json.dumps(report, allow_nan=False)


def test_empty_products_allowed():
    translations, products = make_data()
    _, report = validator.validate_category_translation(translations, products.iloc[:0])
    assert report["valid_rows"] == 2
    assert report["business_indicators"]["unused_translated_distinct_categories"] == 2


def test_main_exports_without_source_changes(tmp_path, monkeypatch):
    translations, products = make_data()
    source_dir = tmp_path / "data"
    source_dir.mkdir()
    translations.to_csv(source_dir / "product_category_name_translation.csv", index=False)
    products.to_csv(source_dir / "olist_products_dataset.csv", index=False)
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.iterdir()}
    monkeypatch.setattr(validator, "DATA_DIR", source_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", source_dir / "processed")
    validator.main()
    result = pd.read_csv(source_dir / "processed/category_translation_validated.csv")
    pd.testing.assert_frame_equal(result[translations.columns], translations)
    report = json.loads((source_dir / "processed/category_translation_quality_report.json").read_text(encoding="utf-8"))
    assert report["valid_rows"] == 2
    assert before == {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
