"""Unit tests for validation engine."""

import pandas as pd
import pytest

from app.schemas import ValidationRules
from app.validators import (
    validate_dataset,
    validate_date_column,
    validate_duplicate_column_names,
    validate_duplicate_rows,
    validate_email_column,
    validate_empty_columns,
    validate_missing_values,
    validate_numeric_column,
    validate_required_columns,
)


def test_validate_required_columns():
    """Verify required columns are detected and missing ones produce errors."""
    df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    
    issues = validate_required_columns(df, ["id", "name", "email", "age"])
    assert len(issues) == 2
    missing_cols = [issue.column for issue in issues]
    assert "email" in missing_cols
    assert "age" in missing_cols
    assert all(issue.severity == "error" for issue in issues)


def test_validate_duplicate_columns():
    """Verify duplicate column names in original header are flagged."""
    headers = ["id", "name", "age", "id", "name"]
    issues = validate_duplicate_column_names(headers)
    assert len(issues) == 2
    dup_names = [issue.column for issue in issues]
    assert "id" in dup_names
    assert "name" in dup_names
    assert all(issue.severity == "error" for issue in issues)


def test_validate_empty_columns():
    """Verify completely blank/null columns are flagged as warnings."""
    df = pd.DataFrame({
        "valid": ["val1", "val2"],
        "empty_none": [None, None],
        "empty_spaces": ["   ", ""],
    })
    issues = validate_empty_columns(df)
    assert len(issues) == 2
    flagged = [i.column for i in issues]
    assert "empty_none" in flagged
    assert "empty_spaces" in flagged


def test_validate_duplicate_rows():
    """Verify duplicate rows are identified with 1-indexed CSV row numbers."""
    df = pd.DataFrame({
        "id": [1, 2, 1],
        "val": ["A", "B", "A"],
    })
    issues = validate_duplicate_rows(df)
    assert len(issues) == 1
    # Row 0 is row 2 in CSV, Row 2 is row 4 in CSV
    assert issues[0].row == 4
    assert issues[0].issue_type == "duplicate_row"
    assert issues[0].severity == "warning"


def test_validate_missing_values():
    """Verify missing, NaN, and whitespace-only cells are detected."""
    df = pd.DataFrame({
        "col1": ["val", None, "   "],
        "col2": [10, 20, 30],
    })
    issues = validate_missing_values(df)
    assert len(issues) == 2
    assert issues[0].row == 3  # index 1 + 2
    assert issues[1].row == 4  # index 2 + 2


def test_validate_numeric_column():
    """Verify numeric type checks for float and integer with error reporting."""
    df = pd.DataFrame({
        "price": ["12.50", "invalid_num", "99.99", None],
        "quantity": ["5", "10", "4.5", "ten"],
    })
    
    float_issues = validate_numeric_column(df, "price", target_type="float")
    assert len(float_issues) == 1
    assert float_issues[0].row == 3
    assert float_issues[0].sample_value == "invalid_num"

    int_issues = validate_numeric_column(df, "quantity", target_type="integer")
    assert len(int_issues) == 2
    int_samples = [i.sample_value for i in int_issues]
    assert "4.5" in int_samples
    assert "ten" in int_samples


def test_validate_date_column():
    """Verify date parsing with both automatic and explicit format detection."""
    df = pd.DataFrame({
        "date_auto": ["2023-01-15", "Jan 12 2024", "not-a-date"],
        "date_strict": ["2023-01-15", "15/01/2023", "2023-12-31"],
    })
    
    auto_issues = validate_date_column(df, "date_auto")
    assert len(auto_issues) == 1
    assert auto_issues[0].sample_value == "not-a-date"

    strict_issues = validate_date_column(df, "date_strict", date_format="%Y-%m-%d")
    assert len(strict_issues) == 1
    assert strict_issues[0].sample_value == "15/01/2023"


def test_validate_email_column():
    """Verify email format validation strictly flags invalid emails and ignores blanks."""
    df = pd.DataFrame({
        "email": [
            "user@example.com",
            "first.last+tag@company.co.uk",
            "not-an-email",
            "@missing-user.com",
            "user@domain",
            None,
        ]
    })
    issues = validate_email_column(df, "email")
    assert len(issues) == 3
    invalid_samples = [i.sample_value for i in issues]
    assert "not-an-email" in invalid_samples
    assert "@missing-user.com" in invalid_samples
    assert "user@domain" in invalid_samples


def test_validate_full_dataset_report():
    """Test full pipeline integration with user-configured rules."""
    df = pd.DataFrame({
        "id": [1, 2, 2],
        "name": ["Alice", "Bob", "Bob"],
        "email": ["alice@domain.com", "bob-at-domain.com", "bob-at-domain.com"],
        "score": ["100", "bad_score", "bad_score"],
    })
    
    rules = ValidationRules(
        required_columns=["id", "name", "missing_col"],
        expected_types={"score": "numeric"},
        email_columns=["email"],
        check_duplicates=True,
    )
    
    report = validate_dataset(df, rules=rules, filename="test_full.csv")
    assert report.total_rows == 3
    assert report.total_columns == 4
    assert report.summary.status == "errors_found"
    assert report.summary.error_count > 0
    assert report.summary.warning_count > 0
