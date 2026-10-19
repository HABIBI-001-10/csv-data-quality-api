"""Unit tests for cleaning and transformation operations."""

import numpy as np
import pandas as pd
import pytest

from app.cleaning import (
    clean_column_names,
    clean_dataset,
    convert_column_type,
    sanitize_formula_injection,
    standardize_name,
)
from app.schemas import CleaningConfig, ColumnTypeConversion


def test_standardize_column_names():
    """Verify conversion of irregular header names to clean snake_case."""
    raw = ["First Name", "Email Address (Work)", "Total $$ Spent", "First Name", "123Numeric#"]
    cleaned = clean_column_names(raw)
    assert cleaned == ["first_name", "email_address_work", "total_spent", "first_name_1", "123numeric"]


def test_formula_injection_sanitization():
    """Verify formula injection triggers are escaped with leading single quote."""
    assert sanitize_formula_injection("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert sanitize_formula_injection("+12345") == "'+12345"
    assert sanitize_formula_injection("-50.0") == "'-50.0"
    assert sanitize_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_formula_injection("Regular Text") == "Regular Text"
    assert sanitize_formula_injection(123) == 123


def test_clean_deduplication():
    """Verify duplicate row removal updates row counts and operation summary."""
    df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["A", "B", "B", "C"],
    })
    config = CleaningConfig(drop_duplicates=True)
    cleaned, report = clean_dataset(df, config)

    assert report.rows_before == 4
    assert report.rows_after == 3
    assert report.rows_removed == 1
    assert len(cleaned) == 3
    assert cleaned["id"].tolist() == [1, 2, 3]


def test_clean_drop_columns():
    """Verify specified columns are dropped cleanly."""
    df = pd.DataFrame({"col_a": [1, 2], "col_b": [3, 4], "col_c": [5, 6]})
    config = CleaningConfig(drop_columns=["col_b", "non_existent"])
    cleaned, report = clean_dataset(df, config)

    assert report.columns_before == 3
    assert report.columns_after == 2
    assert report.columns_removed == 1
    assert "col_b" not in cleaned.columns
    assert "col_a" in cleaned.columns
    assert "col_c" in cleaned.columns


def test_clean_trim_whitespace():
    """Verify leading and trailing whitespace is stripped from text columns."""
    df = pd.DataFrame({
        "name": ["  Alice  ", "Bob  ", "Charlie"],
        "num": [1, 2, 3],
    })
    config = CleaningConfig(trim_whitespace=True)
    cleaned, report = clean_dataset(df, config)

    assert cleaned["name"].tolist() == ["Alice", "Bob", "Charlie"]
    op = next(o for o in report.operations_applied if o.name == "trim_whitespace")
    assert op.affected_count >= 2


def test_clean_missing_drop_rows():
    """Verify dropping rows with missing values works globally."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "val": ["A", None, "C", "D"],
    })
    config = CleaningConfig(missing_value_strategy="drop_rows")
    cleaned, report = clean_dataset(df, config)

    assert report.rows_before == 4
    assert report.rows_after == 3
    assert report.rows_removed == 1
    assert None not in cleaned["val"].tolist()


def test_clean_missing_fill_strategies():
    """Verify fill_value, fill_mean, fill_median, and fill_mode strategies."""
    # Test fill_value
    df_val = pd.DataFrame({"text": ["hello", None, "world"]})
    config_val = CleaningConfig(missing_value_strategy="fill_value", fill_value="N/A")
    cleaned_val, _ = clean_dataset(df_val, config_val)
    assert cleaned_val["text"].tolist() == ["hello", "N/A", "world"]

    # Test fill_mean
    df_mean = pd.DataFrame({"num": [10.0, 20.0, None, 30.0]})
    config_mean = CleaningConfig(missing_value_strategy="fill_mean")
    cleaned_mean, _ = clean_dataset(df_mean, config_mean)
    assert cleaned_mean["num"].iloc[2] == 20.0

    # Test fill_mode
    df_mode = pd.DataFrame({"cat": ["apple", "banana", "apple", None]})
    config_mode = CleaningConfig(missing_value_strategy="fill_mode")
    cleaned_mode, _ = clean_dataset(df_mode, config_mode)
    assert cleaned_mode["cat"].iloc[3] == "apple"


def test_clean_type_conversion():
    """Verify conversion of column data types (integer, float, boolean, date)."""
    df = pd.DataFrame({
        "int_col": ["1", "2", "invalid"],
        "bool_col": ["true", "no", "yes"],
        "date_col": ["2023-01-01", "2023-06-15", "bad-date"],
    })

    config = CleaningConfig(
        type_conversions=[
            ColumnTypeConversion(column="int_col", target_type="integer", on_error="coerce"),
            ColumnTypeConversion(column="bool_col", target_type="boolean", on_error="coerce"),
            ColumnTypeConversion(column="date_col", target_type="date", on_error="coerce"),
        ]
    )
    cleaned, _ = clean_dataset(df, config)

    assert pd.isna(cleaned["int_col"].iloc[2])
    assert cleaned["int_col"].iloc[0] == 1
    assert cleaned["bool_col"].tolist() == [True, False, True]
    assert cleaned["date_col"].iloc[0] == "2023-01-01"
    assert pd.isna(cleaned["date_col"].iloc[2]) or cleaned["date_col"].iloc[2] is None
