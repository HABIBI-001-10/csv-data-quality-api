"""Data cleaning module for transforming and standardizing CSV datasets.

Provides configurable operations:
- Deduplication of rows (all columns or selected subset)
- Dropping selected columns
- Missing value imputation and row-dropping strategies
- Type conversion with error coercion
- Whitespace trimming for textual data
- Column name standardization
- CSV formula injection sanitization
- Before-and-after change tracking and preview generation
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.profiler import sanitize_record_value
from app.schemas import (
    CleaningConfig,
    CleaningOperationSummary,
    CleaningReport,
    ColumnTypeConversion,
)

# Characters that trigger formula execution in spreadsheet software
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_formula_injection(val: Any) -> Any:
    """Neutralize formula injection by prefixing formula triggers with a single quote."""
    if isinstance(val, str):
        trimmed = val.strip()
        if trimmed and trimmed[0] in FORMULA_PREFIXES:
            # Prefix with single quote so Excel/Calc treats it as literal string
            return "'" + val
    return val


def count_missing(df: pd.DataFrame) -> int:
    """Calculate the total number of missing or whitespace-only cells across the DataFrame."""
    count = 0
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            is_na = series.isna() | series.astype(str).str.strip().eq("")
        else:
            is_na = series.isna()
        count += int(is_na.sum())
    return count


def standardize_name(name: str) -> str:
    """Convert an arbitrary column name into a clean snake_case identifier."""
    # Convert to string and lowercase
    s = str(name).strip().lower()
    # Replace non-alphanumeric characters with underscores
    s = re.sub(r"[^a-z0-9]+", "_", s)
    # Remove leading/trailing and duplicate underscores
    s = re.sub(r"_+", "_", s).strip("_")
    return s if s else "column"


def clean_column_names(columns: List[str]) -> List[str]:
    """Standardize a list of column names, ensuring uniqueness."""
    standardized: List[str] = []
    seen: Dict[str, int] = {}
    
    for col in columns:
        base = standardize_name(col)
        if base not in seen:
            seen[base] = 0
            standardized.append(base)
        else:
            seen[base] += 1
            standardized.append(f"{base}_{seen[base]}")
            
    return standardized


def parse_boolean_value(val: Any) -> Optional[bool]:
    """Parse common truthy and falsy strings to native boolean."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip().lower()
    if s in ("true", "1", "t", "yes", "y"):
        return True
    if s in ("false", "0", "f", "no", "n"):
        return False
    return None


def convert_column_type(
    series: pd.Series,
    target_type: str,
    on_error: str = "coerce"
) -> Tuple[pd.Series, int]:
    """Cast a Series to the specified target type.
    
    Returns:
        Tuple of (transformed Series, count of converted/coerced values).
    """
    errors_arg = "coerce" if on_error == "coerce" else "ignore"
    
    if target_type == "integer":
        # Convert to float first, then pandas nullable Int64
        num_series = pd.to_numeric(series, errors=errors_arg)
        try:
            return num_series.astype("Int64"), int(num_series.notna().sum())
        except Exception:
            return num_series, int(num_series.notna().sum())

    elif target_type in ("numeric", "float"):
        num_series = pd.to_numeric(series, errors=errors_arg)
        return num_series, int(num_series.notna().sum())

    elif target_type == "string":
        # Convert nulls to None, others to string
        str_series = series.apply(lambda x: None if pd.isna(x) else str(x))
        return str_series, int(str_series.notna().sum())

    elif target_type == "date":
        date_series = pd.to_datetime(series, errors=errors_arg)
        # Format as ISO YYYY-MM-DD string for clean storage and display
        formatted = date_series.dt.strftime("%Y-%m-%d").replace("NaT", None)
        return formatted, int(formatted.notna().sum())

    elif target_type == "boolean":
        bool_series = series.apply(parse_boolean_value)
        return bool_series, int(bool_series.notna().sum())

    return series, 0


def clean_dataset(
    df: pd.DataFrame,
    config: CleaningConfig,
    filename: str = "cleaned_dataset.csv"
) -> Tuple[pd.DataFrame, CleaningReport]:
    """Apply configured cleaning operations to a DataFrame and produce a report.
    
    Args:
        df: Input DataFrame to clean.
        config: User's cleaning options.
        filename: Name of the output file.
        
    Returns:
        Tuple of (cleaned DataFrame, CleaningReport).
    """
    # Create an explicit working copy
    cleaned = df.copy()

    # Track pre-cleaning metrics
    rows_before = int(len(cleaned))
    cols_before = int(len(cleaned.columns))
    missing_before = count_missing(cleaned)
    duplicates_before = int(cleaned.duplicated().sum()) if rows_before > 0 else 0

    # Build initial preview
    preview_before = [
        {str(c): sanitize_record_value(row[c]) for c in cleaned.columns}
        for _, row in cleaned.head(10).iterrows()
    ]

    operations: List[CleaningOperationSummary] = []

    # 1. Standardize column names (if requested)
    if config.standardize_column_names:
        old_cols = list(cleaned.columns)
        new_cols = clean_column_names(old_cols)
        cleaned.columns = new_cols
        changed_count = sum(1 for o, n in zip(old_cols, new_cols) if o != n)
        operations.append(
            CleaningOperationSummary(
                name="standardize_column_names",
                description=f"Standardized {len(new_cols)} column names to snake_case ({changed_count} modified)",
                affected_count=changed_count,
            )
        )

    # 2. Drop selected columns
    if config.drop_columns:
        # Match columns considering possible standardization
        cols_to_drop = [c for c in config.drop_columns if c in cleaned.columns]
        if cols_to_drop:
            cleaned.drop(columns=cols_to_drop, inplace=True)
            operations.append(
                CleaningOperationSummary(
                    name="drop_columns",
                    description=f"Dropped {len(cols_to_drop)} columns: {', '.join(cols_to_drop)}",
                    affected_count=len(cols_to_drop),
                )
            )

    # 3. Trim whitespace in text columns
    if config.trim_whitespace:
        trimmed_cells = 0
        for col in cleaned.columns:
            series = cleaned[col]
            if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                def _trim(val: Any) -> Any:
                    nonlocal trimmed_cells
                    if isinstance(val, str):
                        s = val.strip()
                        if s != val:
                            trimmed_cells += 1
                        return s if s != "" else None
                    return val

                cleaned[col] = series.apply(_trim)

        if trimmed_cells > 0:
            operations.append(
                CleaningOperationSummary(
                    name="trim_whitespace",
                    description=f"Trimmed leading/trailing whitespace across {trimmed_cells} cells",
                    affected_count=trimmed_cells,
                )
            )

    # 4. Remove duplicate rows
    if config.drop_duplicates:
        initial_count = len(cleaned)
        subset = config.duplicate_subset if config.duplicate_subset else None
        # Verify subset columns exist
        if subset:
            subset = [c for c in subset if c in cleaned.columns]
        cleaned.drop_duplicates(subset=subset, keep="first", inplace=True)
        cleaned.reset_index(drop=True, inplace=True)
        dropped_rows = initial_count - len(cleaned)
        operations.append(
            CleaningOperationSummary(
                name="drop_duplicates",
                description=f"Removed {dropped_rows} duplicate rows",
                affected_count=dropped_rows,
            )
        )

    # 5. Handle missing values
    # Process column overrides first, then global strategy
    missing_cells_filled = 0
    rows_dropped_missing = 0

    # Global drop_rows strategy
    if config.missing_value_strategy == "drop_rows":
        pre_drop = len(cleaned)
        cleaned.dropna(how="any", inplace=True)
        cleaned.reset_index(drop=True, inplace=True)
        rows_dropped_missing = pre_drop - len(cleaned)
        operations.append(
            CleaningOperationSummary(
                name="drop_rows_missing",
                description=f"Dropped {rows_dropped_missing} rows containing missing values",
                affected_count=rows_dropped_missing,
            )
        )
    else:
        # Impute or fill missing values
        for col in cleaned.columns:
            series = cleaned[col]
            strategy = config.column_missing_strategies.get(col, config.missing_value_strategy)
            
            if strategy == "leave":
                continue

            # Identify missing values
            if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                na_mask = series.isna() | series.astype(str).str.strip().eq("")
            else:
                na_mask = series.isna()

            col_missing_count = int(na_mask.sum())
            if col_missing_count == 0:
                continue

            if strategy == "fill_value":
                fill_val = config.column_fill_values.get(col, config.fill_value or "")
                cleaned[col] = cleaned[col].fillna(fill_val)
                # Also fill blank strings if string column
                if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                    cleaned[col] = cleaned[col].replace(r"^\s*$", fill_val, regex=True)
                missing_cells_filled += col_missing_count

            elif strategy == "fill_mean" and pd.api.types.is_numeric_dtype(series):
                mean_val = series.mean()
                if pd.notna(mean_val):
                    cleaned[col] = cleaned[col].fillna(round(mean_val, 4))
                    missing_cells_filled += col_missing_count

            elif strategy == "fill_median" and pd.api.types.is_numeric_dtype(series):
                median_val = series.median()
                if pd.notna(median_val):
                    cleaned[col] = cleaned[col].fillna(round(median_val, 4))
                    missing_cells_filled += col_missing_count

            elif strategy == "fill_mode":
                mode_vals = series.dropna().mode()
                if not mode_vals.empty:
                    mode_val = mode_vals.iloc[0]
                    cleaned[col] = cleaned[col].fillna(mode_val)
                    if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                        cleaned[col] = cleaned[col].replace(r"^\s*$", mode_val, regex=True)
                    missing_cells_filled += col_missing_count

        if missing_cells_filled > 0:
            operations.append(
                CleaningOperationSummary(
                    name="fill_missing_values",
                    description=f"Filled {missing_cells_filled} missing cells using specified strategies",
                    affected_count=missing_cells_filled,
                )
            )

    # 6. Apply type conversions
    for conv in config.type_conversions:
        target_col = conv.column
        if target_col in cleaned.columns:
            new_series, converted_count = convert_column_type(
                cleaned[target_col], conv.target_type, conv.on_error
            )
            cleaned[target_col] = new_series
            operations.append(
                CleaningOperationSummary(
                    name=f"convert_type_{target_col}",
                    description=f"Converted column '{target_col}' to {conv.target_type} ({converted_count} valid entries)",
                    affected_count=converted_count,
                )
            )

    # 7. Protect against formula injection (if enabled)
    if config.sanitize_formulas:
        formula_sanitized_count = 0
        for col in cleaned.columns:
            series = cleaned[col]
            if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                def _sanitize(val: Any) -> Any:
                    nonlocal formula_sanitized_count
                    sanitized = sanitize_formula_injection(val)
                    if sanitized != val:
                        formula_sanitized_count += 1
                    return sanitized

                cleaned[col] = series.apply(_sanitize)

        if formula_sanitized_count > 0:
            operations.append(
                CleaningOperationSummary(
                    name="sanitize_formulas",
                    description=f"Neutralized formula injection triggers in {formula_sanitized_count} cells",
                    affected_count=formula_sanitized_count,
                )
            )

    # Calculate post-cleaning metrics
    rows_after = int(len(cleaned))
    cols_after = int(len(cleaned.columns))
    missing_after = count_missing(cleaned)
    duplicates_after = int(cleaned.duplicated().sum()) if rows_after > 0 else 0

    preview_after = [
        {str(c): sanitize_record_value(row[c]) for c in cleaned.columns}
        for _, row in cleaned.head(10).iterrows()
    ]

    report = CleaningReport(
        filename=filename,
        rows_before=rows_before,
        rows_after=rows_after,
        rows_removed=rows_before - rows_after,
        columns_before=cols_before,
        columns_after=cols_after,
        columns_removed=cols_before - cols_after,
        missing_before=missing_before,
        missing_after=missing_after,
        missing_resolved=max(0, missing_before - missing_after),
        duplicates_before=duplicates_before,
        duplicates_after=duplicates_after,
        operations_applied=operations,
        preview_before=preview_before,
        preview_after=preview_after,
        cleaned_column_names=[str(c) for c in cleaned.columns],
    )

    return cleaned, report
