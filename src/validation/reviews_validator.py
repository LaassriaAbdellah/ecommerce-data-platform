"""Structural Reviews rules and independent business/chronology indicators."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.validation.common import (
    check_required_columns, check_missing_ids, check_duplicate_ids,
    check_invalid_dates,
)
from src.validation.quality_engine import apply_quality_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
DATE_COLUMNS = ["review_creation_date", "review_answer_timestamp"]
REQUIRED_COLUMNS = [
    "review_id", "order_id", "review_score", "review_comment_title",
    "review_comment_message", *DATE_COLUMNS,
]
ORDER_COLUMNS = [
    "order_id", "order_purchase_timestamp", "order_delivered_customer_date",
]


def validate_reviews(reviews: pd.DataFrame, orders: pd.DataFrame):
    """Preserve every source value; only structural rules affect quality.

    Dates in Olist are timezone-naive. Date conversion is for checks only.
    Orders must have a complete unique key so chronology is unambiguous.
    """
    check_required_columns(reviews, REQUIRED_COLUMNS)
    check_required_columns(orders, ORDER_COLUMNS)
    missing_reference = check_missing_ids(orders, "order_id")
    if missing_reference.any() or check_duplicate_ids(orders, "order_id").any():
        raise ValueError("Orders order_id must be nonempty and unique")

    missing_review = check_missing_ids(reviews, "review_id")
    missing_order = check_missing_ids(reviews, "order_id")
    complete_key = ~missing_review & ~missing_order
    score = pd.to_numeric(reviews.review_score, errors="coerce")
    finite = (score.notna() & np.isfinite(score)).fillna(False)
    boolean_score = reviews.review_score.map(
        lambda value: isinstance(value, (bool, np.bool_))
    ).astype(bool)
    valid_score = (
        finite & ~boolean_score & score.between(1, 5)
        & score.where(finite).mod(1).eq(0)
    ).fillna(False)

    date_input = reviews[DATE_COLUMNS].copy()
    missing_dates = {}
    for col in DATE_COLUMNS:
        missing_dates[col] = check_missing_ids(reviews, col)
        date_input[col] = reviews[col].astype("string").where(~missing_dates[col])
    dates, invalid_dates = check_invalid_dates(
        date_input, DATE_COLUMNS, date_format="mixed"
    )
    rules = {
        "missing_review_id": missing_review,
        "missing_order_id": missing_order,
        "duplicate_review_order": (
            check_duplicate_ids(reviews, ["review_id", "order_id"]) & complete_key
        ),
        "invalid_review_score": ~valid_score,
        "unknown_order": ~missing_order & ~reviews.order_id.isin(orders.order_id),
    }
    for col in DATE_COLUMNS:
        rules[f"missing_{col}"] = missing_dates[col]
        rules[f"invalid_{col}"] = invalid_dates[f"invalid_{col}"]
    result, report = apply_quality_rules(reviews, rules, entity_name="reviews")

    pairs = reviews.loc[complete_key, ["review_id", "order_id"]].drop_duplicates()
    counts = pairs.groupby("order_id").review_id.nunique()
    scored = pd.DataFrame({"order_id": reviews.order_id, "score": score},
                          index=reviews.index)
    distinct_scores = scored.loc[complete_key & valid_score].groupby("order_id").score.nunique()
    # Do not infer agreement/disagreement from a partially invalid group.
    invalid_score_orders = reviews.loc[complete_key & ~valid_score, "order_id"]
    distinct_scores = distinct_scores.drop(index=invalid_score_orders.unique(), errors="ignore")
    title_missing = check_missing_ids(reviews, "review_comment_title")
    message_missing = check_missing_ids(reviews, "review_comment_message")
    creation = dates.review_creation_date
    answer = dates.review_answer_timestamp
    delays = (answer - creation).dt.total_seconds().div(86400).dropna()
    order_lookup = orders.set_index("order_id")
    purchase = pd.to_datetime(
        reviews.order_id.map(order_lookup.order_purchase_timestamp),
        format="mixed", errors="coerce",
    )
    delivery = pd.to_datetime(
        reviews.order_id.map(order_lookup.order_delivered_customer_date),
        format="mixed", errors="coerce",
    )
    known = ~missing_order & reviews.order_id.isin(orders.order_id)
    report["business_indicators"] = {
        "missing_title_rows": int(title_missing.sum()),
        "missing_message_rows": int(message_missing.sum()),
        "both_comments_missing_rows": int((title_missing & message_missing).sum()),
        "orders_with_multiple_reviews": int(counts.gt(1).sum()),
        "orders_with_different_scores": int(distinct_scores.gt(1).sum()),
        "orders_without_reviews": int((~orders.order_id.isin(pairs.order_id)).sum()),
        "creation_before_purchase_rows": int(creation.lt(purchase).sum()),
        "answer_before_purchase_rows": int(answer.lt(purchase).sum()),
        "creation_before_delivery_timestamp_rows": int(creation.lt(delivery).sum()),
        "creation_before_delivery_calendar_date_rows": int(
            creation.dt.normalize().lt(delivery.dt.normalize()).sum()
        ),
        "answer_before_delivery_rows": int(answer.lt(delivery).sum()),
        "creation_purchase_comparable_rows": int((creation.notna() & purchase.notna()).sum()),
        "answer_purchase_comparable_rows": int((answer.notna() & purchase.notna()).sum()),
        "creation_delivery_comparable_rows": int((creation.notna() & delivery.notna()).sum()),
        "answer_delivery_comparable_rows": int((answer.notna() & delivery.notna()).sum()),
        "creation_without_usable_delivery_rows": int(
            (known & creation.notna() & delivery.isna()).sum()
        ),
        "creation_at_midnight_rows": int(creation.eq(creation.dt.normalize()).sum()),
    }
    report["answer_delay_days"] = {
        "count": int(len(delays)),
        "min": None if delays.empty else float(delays.min()),
        "median": None if delays.empty else float(delays.median()),
        "mean": None if delays.empty else float(delays.mean()),
        "p95": None if delays.empty else float(delays.quantile(.95)),
        "p99": None if delays.empty else float(delays.quantile(.99)),
        "max": None if delays.empty else float(delays.max()),
        "negative_rows": int(delays.lt(0).sum()),
        "zero_rows": int(delays.eq(0).sum()),
    }
    report["indicator_methodology"] = {
        "grain": "Source review/order association; no rows removed. Multiplicity uses distinct complete pairs, including unknown orders. Orders without reviews uses presence of complete pairs regardless of score/date validity.",
        "scores": "Distinct valid numeric scores per order; exclude groups containing an invalid score. Duplicate pairs are structural errors, not additional distinct reviews.",
        "dates": "Timezone-naive Olist timestamps; mixed parsing. Invalid/missing dates excluded pairwise, never filled. Midnight creation can represent date-level precision.",
        "delivery": "Timestamp comparison uses full values; calendar-date comparison normalizes both to midnight. Missing or unparseable delivery excluded, with comparable counts reported.",
        "delay": "Answer minus creation in 24-hour days, for valid date pairs including negative values. No rejection threshold; not assumed to be a seller response time.",
        "quality": "Business indicators and delays do not affect quality_status, quality_issue_count or quality_issues. Groups may overlap.",
    }
    return result, report


def main():
    reviews = pd.read_csv(DATA_DIR / "olist_order_reviews_dataset.csv")
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv", usecols=ORDER_COLUMNS)
    result, report = validate_reviews(reviews, orders)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_DIR / "reviews_validated.csv", index=False)
    with (OUTPUT_DIR / "reviews_quality_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
