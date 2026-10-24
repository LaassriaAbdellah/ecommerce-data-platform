import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.validation import reviews_validator as validator


def make_data():
    reviews = pd.DataFrame({
        "review_id": ["R1", "R2"],
        "order_id": ["O1", "O2"],
        "review_score": [5, 4],
        "review_comment_title": ["Good", "OK"],
        "review_comment_message": ["Fine", "Fine"],
        "review_creation_date": ["2018-01-03 00:00:00"] * 2,
        "review_answer_timestamp": ["2018-01-04 12:00:00"] * 2,
    })
    orders = pd.DataFrame({
        "order_id": ["O1", "O2"],
        "order_purchase_timestamp": ["2018-01-01 12:00:00"] * 2,
        "order_delivered_customer_date": ["2018-01-02 12:00:00"] * 2,
    })
    return reviews, orders


def change(reviews, column, value):
    result = reviews.copy()
    result[column] = result[column].astype(object)
    result.loc[result.index[0], column] = value
    return result


def test_valid():
    reviews, orders = make_data()
    result, report = validator.validate_reviews(reviews, orders)
    assert report["valid_rows"] == 2 and report["review_rows"] == 0
    assert result.quality_issue_count.eq(0).all()
    assert result.quality_issues.map(json.loads).tolist() == [[], []]
    assert report["answer_delay_days"]["median"] == 1.5


@pytest.mark.parametrize("column", ["review_id", "order_id", *validator.DATE_COLUMNS])
@pytest.mark.parametrize("value", [None, pd.NA, "", "  "])
def test_required_values(column, value):
    reviews, orders = make_data()
    result, report = validator.validate_reviews(change(reviews, column, value), orders)
    assert report["anomalies_by_rule"][f"missing_{column}"] == 1
    assert result.loc[0, "quality_issue_count"] == 1


def test_same_review_on_different_orders_allowed():
    reviews, orders = make_data()
    reviews["review_id"] = "R1"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["review_rows"] == 0


def test_composite_duplicate_all_occurrences():
    reviews, orders = make_data()
    reviews.loc[1, ["review_id", "order_id"]] = ["R1", "O1"]
    _, report = validator.validate_reviews(reviews, orders)
    assert report["anomalies_by_rule"]["duplicate_review_order"] == 2
    assert report["business_indicators"]["orders_with_multiple_reviews"] == 0


def test_incomplete_keys_not_counted_twice():
    reviews, orders = make_data()
    reviews["review_id"] = None
    reviews["order_id"] = "O1"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["anomalies_by_rule"]["duplicate_review_order"] == 0


@pytest.mark.parametrize("score", [0, 6, -1, 1.5, "bad", None, pd.NA, "", float("inf"), -float("inf"), float("nan"), True, np.bool_(True)])
def test_invalid_score(score):
    reviews, orders = make_data()
    _, report = validator.validate_reviews(change(reviews, "review_score", score), orders)
    assert report["anomalies_by_rule"]["invalid_review_score"] == 1


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5, "5", 4.0])
def test_valid_scores(score):
    reviews, orders = make_data()
    _, report = validator.validate_reviews(change(reviews, "review_score", score), orders)
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", validator.DATE_COLUMNS)
@pytest.mark.parametrize("value", ["bad", "2018-02-30", "not-a-date"])
def test_invalid_dates(column, value):
    reviews, orders = make_data()
    _, report = validator.validate_reviews(change(reviews, column, value), orders)
    assert report["anomalies_by_rule"][f"invalid_{column}"] == 1
    assert report["answer_delay_days"]["count"] == 1


def test_convertible_dates_of_different_formats():
    reviews, orders = make_data()
    reviews.loc[0, "review_creation_date"] = "2018-01-03"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["review_rows"] == 0


def test_unknown_order():
    reviews, orders = make_data()
    reviews.loc[0, "order_id"] = "UNKNOWN"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["anomalies_by_rule"]["unknown_order"] == 1
    assert report["business_indicators"]["creation_purchase_comparable_rows"] == 1


@pytest.mark.parametrize("column", ["review_comment_title", "review_comment_message"])
@pytest.mark.parametrize("value", [None, pd.NA, "", "   "])
def test_optional_comments(column, value):
    reviews, orders = make_data()
    _, report = validator.validate_reviews(change(reviews, column, value), orders)
    name = "missing_title_rows" if column.endswith("title") else "missing_message_rows"
    assert report["business_indicators"][name] == 1
    assert report["review_rows"] == 0


def test_multiple_reviews_and_scores_are_indicators():
    reviews, orders = make_data()
    reviews["order_id"] = "O1"
    _, report = validator.validate_reviews(reviews, orders)
    indicators = report["business_indicators"]
    assert indicators["orders_with_multiple_reviews"] == 1
    assert indicators["orders_with_different_scores"] == 1
    assert indicators["orders_without_reviews"] == 1
    assert report["review_rows"] == 0


def test_invalid_score_group_excluded_from_disagreement():
    reviews, orders = make_data()
    reviews["order_id"] = "O1"
    reviews = pd.concat([reviews, change(reviews.iloc[:1], "review_score", "bad")], ignore_index=True)
    _, report = validator.validate_reviews(reviews, orders)
    assert report["business_indicators"]["orders_with_different_scores"] == 0


def test_early_creation_answer_and_negative_delay_are_not_errors():
    reviews, orders = make_data()
    reviews["review_creation_date"] = "2017-12-31 12:00:00"
    reviews["review_answer_timestamp"] = "2017-12-30 12:00:00"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["review_rows"] == 0
    assert report["business_indicators"]["creation_before_purchase_rows"] == 2
    assert report["business_indicators"]["answer_before_purchase_rows"] == 2
    assert report["answer_delay_days"]["negative_rows"] == 2
    assert report["answer_delay_days"]["median"] == -1


def test_delivery_timestamp_differs_from_calendar_date():
    reviews, orders = make_data()
    reviews["review_creation_date"] = "2018-01-02 00:00:00"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["business_indicators"]["creation_before_delivery_timestamp_rows"] == 2
    assert report["business_indicators"]["creation_before_delivery_calendar_date_rows"] == 0
    assert report["review_rows"] == 0


@pytest.mark.parametrize("value", [None, "", "bad"])
def test_unusable_delivery_is_excluded(value):
    reviews, orders = make_data()
    orders.loc[0, "order_delivered_customer_date"] = value
    _, report = validator.validate_reviews(reviews, orders)
    indicators = report["business_indicators"]
    assert indicators["creation_delivery_comparable_rows"] == 1
    assert indicators["creation_without_usable_delivery_rows"] == 1
    assert report["review_rows"] == 0


@pytest.mark.parametrize("column", validator.REQUIRED_COLUMNS)
def test_missing_review_column(column):
    reviews, orders = make_data()
    with pytest.raises(ValueError, match=column):
        validator.validate_reviews(reviews.drop(columns=column), orders)


@pytest.mark.parametrize("column", validator.ORDER_COLUMNS)
def test_missing_order_column(column):
    reviews, orders = make_data()
    with pytest.raises(ValueError, match=column):
        validator.validate_reviews(reviews, orders.drop(columns=column))


@pytest.mark.parametrize("value", ["O1", None, " "])
def test_ambiguous_reference_table_rejected(value):
    reviews, orders = make_data()
    orders.loc[1, "order_id"] = value
    with pytest.raises(ValueError, match="unique"):
        validator.validate_reviews(reviews, orders)


def test_inputs_and_custom_index_unchanged():
    reviews, orders = make_data()
    reviews.index = [10, 20]
    originals = [reviews.copy(deep=True), orders.copy(deep=True)]
    result, _ = validator.validate_reviews(reviews, orders)
    pd.testing.assert_frame_equal(reviews, originals[0])
    pd.testing.assert_frame_equal(orders, originals[1])
    pd.testing.assert_frame_equal(result[reviews.columns], reviews)


def test_empty_reviews_and_strict_json():
    reviews, orders = make_data()
    result, report = validator.validate_reviews(reviews.iloc[:0], orders)
    assert result.empty and report["total_rows"] == 0
    assert report["business_indicators"]["orders_without_reviews"] == 2
    assert report["answer_delay_days"]["count"] == 0
    assert report["answer_delay_days"]["median"] is None
    json.dumps(report, allow_nan=False)


def test_all_invalid_dates_give_null_statistics():
    reviews, orders = make_data()
    reviews["review_creation_date"] = "bad"
    _, report = validator.validate_reviews(reviews, orders)
    assert report["answer_delay_days"]["max"] is None
    json.dumps(report, allow_nan=False)


def test_main_exports_preserving_source_bytes(tmp_path, monkeypatch):
    reviews, orders = make_data()
    reviews.loc[0, "review_comment_message"] = 'Text with comma, newline\nand "quotes"'
    source_dir = tmp_path / "data"
    source_dir.mkdir()
    reviews.to_csv(source_dir / "olist_order_reviews_dataset.csv", index=False)
    orders.to_csv(source_dir / "olist_orders_dataset.csv", index=False)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.iterdir()}
    monkeypatch.setattr(validator, "DATA_DIR", source_dir)
    monkeypatch.setattr(validator, "OUTPUT_DIR", source_dir / "processed")
    validator.main()
    saved = pd.read_csv(source_dir / "processed/reviews_validated.csv")
    pd.testing.assert_frame_equal(saved[reviews.columns], reviews)
    report = json.loads((source_dir / "processed/reviews_quality_report.json").read_text(encoding="utf-8"))
    assert report["valid_rows"] == 2
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
