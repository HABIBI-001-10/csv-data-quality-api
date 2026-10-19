"""Unit tests for dataset profiling functionality."""

import numpy as np
import pandas as pd
import pytest

from app.profiler import get_column_stats, profile_dataset, sanitize_float, sanitize_record_value


def test_sanitize_helpers():
    """Verify numeric sanitization handles NaN, inf, and regular floats properly."""
    assert sanitize_float(None) is None
    assert sanitize_float(float("nan")) is None
    assert sanitize_float(float("inf")) is None
    assert sanitize_float(12.34567) == 12.3457
    assert sanitize_record_value(np.int64(42)) == 42
    assert sanitize_record_value(np.float64(3.14)) == 3.14
    assert sanitize_record_value(np.nan) is None
    assert sanitize_record_value("hello") == "hello"


def test_profile_basic_dataset():
    """Verify profiling returns correct dimensions, column stats, duplicates, and preview."""
    data = {
        "id": [1, 2, 3, 3],
        "name": ["Alice", "Bob", "Charlie", "Charlie"],
        "score": [85.5, 92.0, np.nan, np.nan],
        "active": [True, False, True, True],
    }
    df = pd.DataFrame(data)
    report = profile_dataset(df, filename="test.csv")

    assert report.filename == "test.csv"
    assert report.total_rows == 4
    assert report.total_columns == 4
    assert report.duplicate_rows == 1
    assert report.duplicate_percentage == 25.0

    # Check score column profile
    score_profile = next(c for c in report.columns if c.name == "score")
    assert score_profile.missing_count == 2
    assert score_profile.missing_percentage == 50.0
    assert score_profile.stats is not None
    assert score_profile.stats.count == 2
    assert score_profile.stats.mean == round((85.5 + 92.0) / 2, 4)

    # Check preview count
    assert len(report.preview) == 4
    assert report.preview[0]["name"] == "Alice"
    assert report.preview[2]["score"] is None


def test_profile_empty_dataset():
    """Verify profiler handles empty DataFrames safely without crashing."""
    df = pd.DataFrame(columns=["a", "b"])
    report = profile_dataset(df, filename="empty.csv")

    assert report.total_rows == 0
    assert report.total_columns == 2
    assert report.duplicate_rows == 0
    assert report.preview == []
    assert report.columns[0].is_empty is True


def test_profile_all_missing_column():
    """Verify profiler flags completely empty columns correctly."""
    df = pd.DataFrame({
        "filled": ["a", "b", "c"],
        "empty": [None, "", "   "],
    })
    report = profile_dataset(df, filename="missing.csv")
    empty_col = next(c for c in report.columns if c.name == "empty")
    assert empty_col.missing_count == 3
    assert empty_col.is_empty is True
