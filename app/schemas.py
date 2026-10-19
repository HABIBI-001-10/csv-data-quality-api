"""Pydantic schemas for request validation, configuration, and API responses.

This module defines all data transfer objects (DTOs) used throughout the application,
ensuring strict type validation and clear API contracts.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Profiling Schemas
# ---------------------------------------------------------------------------

class ColumnStats(BaseModel):
    """Statistical summary for numeric columns."""
    count: int = Field(description="Number of non-null values")
    mean: Optional[float] = Field(None, description="Average value")
    std: Optional[float] = Field(None, description="Standard deviation")
    min: Optional[float] = Field(None, description="Minimum value")
    p25: Optional[float] = Field(None, description="25th percentile (Q1)")
    median: Optional[float] = Field(None, description="50th percentile (Median)")
    p75: Optional[float] = Field(None, description="75th percentile (Q3)")
    max: Optional[float] = Field(None, description="Maximum value")


class ColumnProfile(BaseModel):
    """Detailed profile information for a single column."""
    name: str = Field(description="Column name")
    data_type: str = Field(description="Inferred data type in pandas")
    missing_count: int = Field(description="Count of missing or blank values")
    missing_percentage: float = Field(description="Percentage of missing values")
    unique_count: int = Field(description="Count of distinct values")
    is_empty: bool = Field(description="Whether the entire column has no values")
    sample_values: List[Any] = Field(default_factory=list, description="A few distinct sample values")
    stats: Optional[ColumnStats] = Field(None, description="Numeric statistics if applicable")


class ProfileReport(BaseModel):
    """Full dataset profiling report."""
    filename: str = Field(description="Uploaded CSV filename")
    total_rows: int = Field(description="Total number of rows")
    total_columns: int = Field(description="Total number of columns")
    column_names: List[str] = Field(description="List of column names in order")
    duplicate_rows: int = Field(description="Count of duplicate rows")
    duplicate_percentage: float = Field(description="Percentage of duplicate rows")
    columns: List[ColumnProfile] = Field(description="Per-column profile statistics")
    preview: List[Dict[str, Any]] = Field(description="First 10 rows of the dataset")
    memory_usage_kb: float = Field(description="Dataset memory footprint in KB")


# ---------------------------------------------------------------------------
# Validation Configuration & Issue Schemas
# ---------------------------------------------------------------------------

IssueSeverity = Literal["error", "warning"]
IssueType = Literal[
    "missing_value",
    "duplicate_row",
    "empty_column",
    "invalid_numeric",
    "invalid_date",
    "invalid_email",
    "missing_required_column",
    "duplicate_column_name",
    "unsupported_type",
]


class ValidationIssue(BaseModel):
    """Individual data-quality issue found during validation."""
    id: str = Field(description="Unique issue identifier")
    column: Optional[str] = Field(None, description="Affected column name, if applicable")
    row: Optional[int] = Field(None, description="1-indexed row number, if applicable")
    issue_type: IssueType = Field(description="Category of the quality issue")
    severity: IssueSeverity = Field(description="Severity: 'error' or 'warning'")
    message: str = Field(description="Human-readable description of the issue")
    sample_value: Optional[str] = Field(None, description="Sample faulty value if available")


class ValidationRules(BaseModel):
    """User-configured validation rules applied to the dataset."""
    required_columns: List[str] = Field(
        default_factory=list,
        description="Columns that must be present in the CSV"
    )
    expected_types: Dict[str, Literal["numeric", "integer", "float", "date", "email", "string", "boolean"]] = Field(
        default_factory=dict,
        description="Mapping of column name to expected logical data type"
    )
    email_columns: List[str] = Field(
        default_factory=list,
        description="Columns explicitly identified by user as containing email addresses"
    )
    date_columns: List[str] = Field(
        default_factory=list,
        description="Columns explicitly identified by user as containing date values"
    )
    date_format: Optional[str] = Field(
        None,
        description="Optional explicit strftime format string (e.g. '%Y-%m-%d')"
    )
    check_duplicates: bool = Field(
        default=True,
        description="Whether to scan for duplicate rows"
    )
    check_empty_columns: bool = Field(
        default=True,
        description="Whether to flag completely empty columns"
    )
    check_missing_values: bool = Field(
        default=True,
        description="Whether to flag missing or blank values"
    )


class ValidationSummary(BaseModel):
    """High-level summary of validation findings."""
    total_issues: int
    error_count: int
    warning_count: int
    status: Literal["passed", "warnings_found", "errors_found"]


class ValidationReport(BaseModel):
    """Complete validation report output."""
    filename: str
    total_rows: int
    total_columns: int
    summary: ValidationSummary
    rules_applied: ValidationRules
    issues: List[ValidationIssue]
    issues_by_column: Dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cleaning Options & Summary Schemas
# ---------------------------------------------------------------------------

MissingValueStrategy = Literal["leave", "drop_rows", "fill_value", "fill_mean", "fill_median", "fill_mode"]


class ColumnTypeConversion(BaseModel):
    """Type conversion specification for a column."""
    column: str
    target_type: Literal["integer", "float", "string", "date", "boolean"]
    on_error: Literal["coerce", "ignore"] = "coerce"


class CleaningConfig(BaseModel):
    """User-selectable options for cleaning the dataset."""
    drop_duplicates: bool = Field(
        default=False,
        description="Remove exact duplicate rows across all columns or selected subset"
    )
    duplicate_subset: Optional[List[str]] = Field(
        None,
        description="Optional list of column names to consider when identifying duplicates"
    )
    drop_columns: List[str] = Field(
        default_factory=list,
        description="List of column names to drop completely"
    )
    trim_whitespace: bool = Field(
        default=True,
        description="Trim leading and trailing whitespace from string/text columns"
    )
    standardize_column_names: bool = Field(
        default=False,
        description="Convert column names to lower_snake_case and strip special characters"
    )
    missing_value_strategy: MissingValueStrategy = Field(
        default="leave",
        description="Global missing-value strategy: 'leave', 'drop_rows', 'fill_value', 'fill_mean', 'fill_median', 'fill_mode'"
    )
    fill_value: Optional[str] = Field(
        None,
        description="Value to use when missing_value_strategy is 'fill_value'"
    )
    column_missing_strategies: Dict[str, MissingValueStrategy] = Field(
        default_factory=dict,
        description="Per-column override for missing value strategy"
    )
    column_fill_values: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-column specific fill values when using 'fill_value'"
    )
    type_conversions: List[ColumnTypeConversion] = Field(
        default_factory=list,
        description="Columns to cast to target data types"
    )
    sanitize_formulas: bool = Field(
        default=True,
        description="Escape leading '=', '+', '-', '@' to prevent CSV formula injection"
    )


class CleaningOperationSummary(BaseModel):
    """Detailed record of a single cleaning step performed."""
    name: str = Field(description="Name of operation (e.g. 'drop_duplicates')")
    description: str = Field(description="Human-readable description of what changed")
    affected_count: int = Field(description="Number of rows, columns, or cells affected")


class CleaningReport(BaseModel):
    """Complete summary of before-and-after cleaning results."""
    filename: str
    rows_before: int
    rows_after: int
    rows_removed: int
    columns_before: int
    columns_after: int
    columns_removed: int
    missing_before: int
    missing_after: int
    missing_resolved: int
    duplicates_before: int
    duplicates_after: int
    operations_applied: List[CleaningOperationSummary]
    preview_before: List[Dict[str, Any]]
    preview_after: List[Dict[str, Any]]
    cleaned_column_names: List[str]


# ---------------------------------------------------------------------------
# General API Response Schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app_name: str
    version: str


class ErrorResponse(BaseModel):
    """Standardized API error response schema."""
    error: str = Field(description="Error type identifier")
    message: str = Field(description="Detailed error message")
    details: Optional[Any] = Field(None, description="Optional extra details")
