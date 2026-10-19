"""Data profiling module for CSV datasets.

Provides comprehensive summary statistics, schema analysis, missing-value
breakdowns, duplicate counts, and preview records for uploaded datasets.
"""

from typing import Any, Dict, List, Optional
import math
import numpy as np
import pandas as pd

from app.schemas import ColumnProfile, ColumnStats, ProfileReport


def sanitize_float(val: Any) -> Optional[float]:
    """Convert numpy/pandas floats to standard Python float, replacing NaN/inf with None."""
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def sanitize_record_value(val: Any) -> Any:
    """Sanitize a single cell value for clean JSON serialization."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return sanitize_float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    return str(val)


def get_column_stats(series: pd.Series) -> Optional[ColumnStats]:
    """Calculate basic numeric summary statistics for a numeric column."""
    # Check if the series is numeric
    if not pd.api.types.is_numeric_dtype(series):
        return None

    valid = series.dropna()
    if valid.empty:
        return None

    try:
        desc = valid.describe(percentiles=[0.25, 0.5, 0.75])
        return ColumnStats(
            count=int(desc.get("count", 0)),
            mean=sanitize_float(desc.get("mean")),
            std=sanitize_float(desc.get("std")),
            min=sanitize_float(desc.get("min")),
            p25=sanitize_float(desc.get("25%")),
            median=sanitize_float(desc.get("50%")),
            p75=sanitize_float(desc.get("75%")),
            max=sanitize_float(desc.get("max")),
        )
    except Exception:
        return None


def profile_dataset(df: pd.DataFrame, filename: str = "dataset.csv") -> ProfileReport:
    """Analyze a DataFrame and return a complete ProfileReport.
    
    Args:
        df: The pandas DataFrame to profile.
        filename: Name of the uploaded file.
        
    Returns:
        ProfileReport containing structural and statistical metadata.
    """
    total_rows = int(len(df))
    total_cols = int(len(df.columns))
    column_names = [str(col) for col in df.columns]

    # Calculate duplicate rows
    if total_rows > 0:
        dup_mask = df.duplicated()
        duplicate_rows = int(dup_mask.sum())
        duplicate_pct = round((duplicate_rows / total_rows) * 100, 2)
    else:
        duplicate_rows = 0
        duplicate_pct = 0.0

    # Build per-column profiles
    col_profiles: List[ColumnProfile] = []
    for col_name in df.columns:
        series = df[col_name]
        
        # Missing values include pandas NA/null as well as empty or whitespace-only strings
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            # Treat empty/whitespace-only strings as missing for profiling count
            is_na = series.isna() | series.astype(str).str.strip().eq("")
        else:
            is_na = series.isna()

        missing_count = int(is_na.sum())
        missing_pct = round((missing_count / total_rows * 100), 2) if total_rows > 0 else 0.0

        # Unique non-null values
        non_null_series = series[~is_na]
        unique_count = int(non_null_series.nunique())

        # Sample values (up to 4 non-null distinct items)
        sample_vals: List[Any] = []
        if not non_null_series.empty:
            raw_samples = non_null_series.drop_duplicates().head(4).tolist()
            sample_vals = [sanitize_record_value(s) for s in raw_samples]

        is_empty = missing_count == total_rows if total_rows > 0 else True
        stats = get_column_stats(series)

        col_profiles.append(
            ColumnProfile(
                name=str(col_name),
                data_type=str(series.dtype),
                missing_count=missing_count,
                missing_percentage=missing_pct,
                unique_count=unique_count,
                is_empty=is_empty,
                sample_values=sample_vals,
                stats=stats,
            )
        )

    # First 10 rows preview
    preview_df = df.head(10)
    preview: List[Dict[str, Any]] = []
    for _, row in preview_df.iterrows():
        record: Dict[str, Any] = {}
        for col in df.columns:
            record[str(col)] = sanitize_record_value(row[col])
        preview.append(record)

    # Memory usage in KB
    try:
        mem_bytes = df.memory_usage(deep=True).sum()
        memory_usage_kb = round(float(mem_bytes) / 1024.0, 2)
    except Exception:
        memory_usage_kb = 0.0

    return ProfileReport(
        filename=filename,
        total_rows=total_rows,
        total_columns=total_cols,
        column_names=column_names,
        duplicate_rows=duplicate_rows,
        duplicate_percentage=duplicate_pct,
        columns=col_profiles,
        preview=preview,
        memory_usage_kb=memory_usage_kb,
    )
