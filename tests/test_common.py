
import pandas as pd
import pytest

from src.validation.common import (
    check_required_columns,
    check_missing_ids,
    check_duplicate_ids,
    check_invalid_dates,
)


def test_required_columns():
    df = pd.DataFrame({"id": [1, 2]})

    check_required_columns(df, ["id"])

    with pytest.raises(ValueError):
        check_required_columns(df, ["id", "name"])


def test_missing_ids():
    df = pd.DataFrame({
        "id": ["A1", None, "", "   ", "A5"]
    })

    result = check_missing_ids(df, "id")

    assert result.tolist() == [
        False, True, True, True, False
    ]


def test_duplicate_ids():
    df = pd.DataFrame({
        "id": ["A1", "A2", "A1"]
    })

    result = check_duplicate_ids(df, "id")

    assert result.tolist() == [True, False, True]


def test_invalid_dates():
    df = pd.DataFrame({
        "date": ["2026-01-01", "invalid", None]
    })

    converted, rules = check_invalid_dates(df, ["date"])

    assert rules["invalid_date"].tolist() == [
        False, True, False
    ]

    assert pd.api.types.is_datetime64_any_dtype(
        converted["date"]
    )
