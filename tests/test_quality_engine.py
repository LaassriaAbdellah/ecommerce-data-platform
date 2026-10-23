
import json

import pandas as pd
import pytest

from src.validation.quality_engine import apply_quality_rules


def test_no_anomalies():
    df = pd.DataFrame({"id": ["A1", "A2"]})

    rules = {
        "missing_id": df["id"].isna(),
    }

    result, report = apply_quality_rules(
        df, rules, "example"
    )

    assert report["total_rows"] == 2
    assert report["valid_rows"] == 2
    assert report["review_rows"] == 0
    assert result["quality_status"].eq("valid").all()


def test_multiple_anomalies():
    df = pd.DataFrame({
        "id": ["A1", None, "A1"]
    })

    rules = {
        "missing_id": df["id"].isna(),
        "duplicate_id": df["id"].duplicated(keep=False),
    }

    result, report = apply_quality_rules(
        df, rules, "example"
    )

    assert report["total_rows"] == 3
    assert report["review_rows"] == 3

    assert result["quality_issue_count"].tolist() == [
        1, 1, 1
    ]

    assert json.loads(
        result.loc[1, "quality_issues"]
    ) == ["missing_id"]


def test_no_rules():
    df = pd.DataFrame({"id": ["A1", "A2"]})

    result, report = apply_quality_rules(
        df, {}, "example"
    )

    assert report["valid_rows"] == 2
    assert report["anomalies_by_rule"] == {}
    assert result["quality_issue_count"].eq(0).all()


def test_invalid_rule_index():
    df = pd.DataFrame({"id": ["A1", "A2"]})

    rules = {
        "invalid": pd.Series(
            [True, False],
            index=[10, 11]
        )
    }

    with pytest.raises(ValueError):
        apply_quality_rules(df, rules, "example")


def test_original_dataframe_unchanged():
    df = pd.DataFrame({"id": ["A1", None]})
    original = df.copy(deep=True)

    rules = {
        "missing_id": df["id"].isna()
    }

    apply_quality_rules(df, rules, "example")

    pd.testing.assert_frame_equal(df, original)
