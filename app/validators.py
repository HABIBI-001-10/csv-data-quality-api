"""Validation engine for detecting data-quality issues in CSV datasets.

Provides modular, reusable validation functions to detect:
- Missing or blank values
- Duplicate records
- Completely empty columns
- Invalid numeric values
- Invalid dates
- Invalid email addresses (strictly when configured by user)
- Missing required columns
- Duplicate column names
"""

import re
from typing import Any, Dict, List, Optional
import dateutil.parser
import pandas as pd

from app.schemas import (
    IssueSeverity,
    IssueType,
    ValidationIssue,
    ValidationReport,
    ValidationRules,
    ValidationSummary,
)

# Standard RFC 5322-compliant simplified email regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
)


def is_blank_or_na(val: Any) -> bool:
    """Check if a cell value is missing, None, NaN, or whitespace-only string."""
    if val is None or pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: List[str]
) -> List[ValidationIssue]:
    """Check if all user-specified required columns are present in the DataFrame."""
    issues: List[ValidationIssue] = []
    current_columns = set(str(c) for c in df.columns)

    for req_col in required_columns:
        if req_col not in current_columns:
            issues.append(
                ValidationIssue(
                    id=f"req-col-{req_col}",
                    column=req_col,
                    row=None,
                    issue_type="missing_required_column",
                    severity="error",
                    message=f"Required column '{req_col}' is missing from the dataset.",
                    sample_value=None,
                )
            )
    return issues


def validate_duplicate_column_names(
    raw_column_names: List[str]
) -> List[ValidationIssue]:
    """Check if there are duplicate column names in the raw header."""
    issues: List[ValidationIssue] = []
    seen = set()
    duplicates = set()
    for col in raw_column_names:
        norm = col.strip()
        if norm in seen:
            duplicates.add(norm)
        else:
            seen.add(norm)

    for dup in sorted(duplicates):
        issues.append(
            ValidationIssue(
                id=f"dup-col-{dup}",
                column=dup,
                row=1,
                issue_type="duplicate_column_name",
                severity="error",
                message=f"Header contains duplicate column name: '{dup}'.",
                sample_value=dup,
            )
        )
    return issues


def validate_empty_columns(df: pd.DataFrame) -> List[ValidationIssue]:
    """Flag columns that contain only null or blank values."""
    issues: List[ValidationIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        # Check if every row is missing/blank
        all_blank = series.apply(is_blank_or_na).all()
        if all_blank:
            issues.append(
                ValidationIssue(
                    id=f"empty-col-{col}",
                    column=str(col),
                    row=None,
                    issue_type="empty_column",
                    severity="warning",
                    message=f"Column '{col}' is completely empty (all {total_rows} rows are blank or null).",
                    sample_value=None,
                )
            )
    return issues


def validate_duplicate_rows(df: pd.DataFrame) -> List[ValidationIssue]:
    """Detect exact duplicate records in the DataFrame."""
    issues: List[ValidationIssue] = []
    if len(df) <= 1:
        return issues

    # Identify duplicates (mark all duplicates as True except first occurrence)
    dup_mask = df.duplicated(keep="first")
    dup_indices = df[dup_mask].index.tolist()

    for idx in dup_indices:
        # 1-indexed: CSV row number (header is row 1, data starts row 2)
        csv_row_num = idx + 2
        issues.append(
            ValidationIssue(
                id=f"dup-row-{csv_row_num}",
                column=None,
                row=csv_row_num,
                issue_type="duplicate_row",
                severity="warning",
                message=f"Row {csv_row_num} is an exact duplicate of an earlier record.",
                sample_value=None,
            )
        )
    return issues


def validate_missing_values(df: pd.DataFrame) -> List[ValidationIssue]:
    """Detect missing or blank values in each cell."""
    issues: List[ValidationIssue] = []
    
    for col in df.columns:
        col_str = str(col)
        series = df[col]
        blank_mask = series.apply(is_blank_or_na)
        blank_indices = df[blank_mask].index.tolist()
        
        for idx in blank_indices:
            csv_row_num = idx + 2
            issues.append(
                ValidationIssue(
                    id=f"missing-{col_str}-{csv_row_num}",
                    column=col_str,
                    row=csv_row_num,
                    issue_type="missing_value",
                    severity="warning",
                    message=f"Missing or blank value in column '{col_str}' at row {csv_row_num}.",
                    sample_value=None,
                )
            )
    return issues


def validate_numeric_column(
    df: pd.DataFrame,
    column: str,
    target_type: str = "numeric"
) -> List[ValidationIssue]:
    """Check that non-blank values in the specified column are valid numbers."""
    issues: List[ValidationIssue] = []
    if column not in df.columns:
        return issues

    series = df[column]
    for idx, val in series.items():
        if is_blank_or_na(val):
            continue

        raw_str = str(val).strip()
        csv_row_num = idx + 2

        if target_type == "integer":
            try:
                # Check if it represents a clean integer
                f = float(raw_str)
                if not f.is_integer():
                    issues.append(
                        ValidationIssue(
                            id=f"invalid-int-{column}-{csv_row_num}",
                            column=column,
                            row=csv_row_num,
                            issue_type="invalid_numeric",
                            severity="error",
                            message=f"Value '{raw_str}' in column '{column}' at row {csv_row_num} is not a valid integer.",
                            sample_value=raw_str,
                        )
                    )
            except ValueError:
                issues.append(
                    ValidationIssue(
                        id=f"invalid-int-{column}-{csv_row_num}",
                        column=column,
                        row=csv_row_num,
                        issue_type="invalid_numeric",
                        severity="error",
                        message=f"Value '{raw_str}' in column '{column}' at row {csv_row_num} cannot be parsed as an integer.",
                        sample_value=raw_str,
                    )
                )
        else:  # numeric or float
            try:
                float(raw_str)
            except ValueError:
                issues.append(
                    ValidationIssue(
                        id=f"invalid-num-{column}-{csv_row_num}",
                        column=column,
                        row=csv_row_num,
                        issue_type="invalid_numeric",
                        severity="error",
                        message=f"Value '{raw_str}' in column '{column}' at row {csv_row_num} cannot be parsed as a number.",
                        sample_value=raw_str,
                    )
                )
    return issues


def validate_date_column(
    df: pd.DataFrame,
    column: str,
    date_format: Optional[str] = None
) -> List[ValidationIssue]:
    """Validate that non-blank values in a date column are parseable as valid dates."""
    issues: List[ValidationIssue] = []
    if column not in df.columns:
        return issues

    series = df[column]
    for idx, val in series.items():
        if is_blank_or_na(val):
            continue

        raw_str = str(val).strip()
        csv_row_num = idx + 2

        parsed = False
        if date_format:
            try:
                pd.to_datetime(raw_str, format=date_format)
                parsed = True
            except Exception:
                parsed = False
        else:
            try:
                # Try dateutil parser
                dateutil.parser.parse(raw_str)
                parsed = True
            except Exception:
                parsed = False

        if not parsed:
            fmt_desc = f" (expected format: {date_format})" if date_format else ""
            issues.append(
                ValidationIssue(
                    id=f"invalid-date-{column}-{csv_row_num}",
                    column=column,
                    row=csv_row_num,
                    issue_type="invalid_date",
                    severity="error",
                    message=f"Value '{raw_str}' in column '{column}' at row {csv_row_num} is not a valid date{fmt_desc}.",
                    sample_value=raw_str,
                )
            )
    return issues


def validate_email_column(df: pd.DataFrame, column: str) -> List[ValidationIssue]:
    """Validate that non-blank values in the user-specified email column conform to standard email syntax."""
    issues: List[ValidationIssue] = []
    if column not in df.columns:
        return issues

    series = df[column]
    for idx, val in series.items():
        if is_blank_or_na(val):
            continue

        raw_str = str(val).strip()
        csv_row_num = idx + 2

        if not EMAIL_REGEX.match(raw_str):
            issues.append(
                ValidationIssue(
                    id=f"invalid-email-{column}-{csv_row_num}",
                    column=column,
                    row=csv_row_num,
                    issue_type="invalid_email",
                    severity="error",
                    message=f"Value '{raw_str}' in column '{column}' at row {csv_row_num} is not a valid email address.",
                    sample_value=raw_str,
                )
            )
    return issues


def validate_dataset(
    df: pd.DataFrame,
    rules: Optional[ValidationRules] = None,
    filename: str = "dataset.csv",
    raw_column_names: Optional[List[str]] = None,
) -> ValidationReport:
    """Run all configured validation rules against the DataFrame and generate a report.
    
    Args:
        df: Pandas DataFrame to validate.
        rules: User-configured rules (or defaults).
        filename: Name of the uploaded file.
        raw_column_names: Raw column header list before deduplication.
        
    Returns:
        ValidationReport with all detected issues and a summary.
    """
    if rules is None:
        rules = ValidationRules()

    all_issues: List[ValidationIssue] = []

    # 1. Check duplicate column names in original header if provided
    if raw_column_names:
        all_issues.extend(validate_duplicate_column_names(raw_column_names))

    # 2. Check required columns
    if rules.required_columns:
        all_issues.extend(validate_required_columns(df, rules.required_columns))

    # 3. Check completely empty columns
    if rules.check_empty_columns:
        all_issues.extend(validate_empty_columns(df))

    # 4. Check duplicate rows
    if rules.check_duplicates:
        all_issues.extend(validate_duplicate_rows(df))

    # 5. Check missing values
    if rules.check_missing_values:
        all_issues.extend(validate_missing_values(df))

    # 6. Check expected types
    for col, expected_type in rules.expected_types.items():
        if expected_type in ("numeric", "integer", "float"):
            all_issues.extend(validate_numeric_column(df, col, expected_type))
        elif expected_type == "date":
            all_issues.extend(validate_date_column(df, col, rules.date_format))
        elif expected_type == "email":
            all_issues.extend(validate_email_column(df, col))

    # 7. Check user-configured explicit email columns (if not already checked)
    for email_col in rules.email_columns:
        if email_col not in rules.expected_types:
            all_issues.extend(validate_email_column(df, email_col))

    # 8. Check user-configured explicit date columns (if not already checked)
    for date_col in rules.date_columns:
        if date_col not in rules.expected_types:
            all_issues.extend(validate_date_column(df, date_col, rules.date_format))

    # Compute summaries
    error_count = sum(1 for issue in all_issues if issue.severity == "error")
    warning_count = sum(1 for issue in all_issues if issue.severity == "warning")
    total_issues = len(all_issues)

    if error_count > 0:
        status = "errors_found"
    elif warning_count > 0:
        status = "warnings_found"
    else:
        status = "passed"

    # Group counts by column
    issues_by_col: Dict[str, int] = {}
    for issue in all_issues:
        col_key = issue.column or "(dataset-level)"
        issues_by_col[col_key] = issues_by_col.get(col_key, 0) + 1

    summary = ValidationSummary(
        total_issues=total_issues,
        error_count=error_count,
        warning_count=warning_count,
        status=status,
    )

    return ValidationReport(
        filename=filename,
        total_rows=len(df),
        total_columns=len(df.columns),
        summary=summary,
        rules_applied=rules,
        issues=all_issues,
        issues_by_column=issues_by_col,
    )
