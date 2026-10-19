"""Service layer for CSV file ingestion, encoding detection, and file exports.

Handles:
- Upload size validation and memory safeguards
- UTF-8 and UTF-8-BOM encoding detection
- Malformed and empty CSV detection
- Duplicate column name detection from raw headers
- CSV serialization for downloads
- Path traversal prevention for file names
"""

import io
import os
import re
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
import pandas as pd

# Default configuration limits
DEFAULT_MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = DEFAULT_MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv"}


def sanitize_filename(filename: Optional[str], default_name: str = "dataset.csv") -> str:
    """Sanitize an uploaded or generated filename to prevent directory traversal attacks."""
    if not filename:
        return default_name

    # Extract base name to remove any directory paths (../ or C:\)
    base = os.path.basename(filename)
    # Strip any characters except alphanumeric, dashes, underscores, and dots
    cleaned = re.sub(r"[^\w\.-]", "_", base)
    if not cleaned.lower().endswith(".csv"):
        cleaned += ".csv"
    return cleaned if cleaned else default_name


def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode raw CSV bytes using robust encoding fallbacks (UTF-8-SIG, UTF-8, Latin-1, CP1252).
    
    Raises:
        HTTPException: If the file cannot be decoded as valid text.
    """
    encodings_to_try = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    
    for enc in encodings_to_try:
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file encoding. Please upload a UTF-8 or standard ASCII encoded CSV.",
    )


async def read_uploaded_csv(
    file: UploadFile,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES
) -> Tuple[pd.DataFrame, List[str], str]:
    """Validate, read, and parse an uploaded CSV file from an UploadFile object.
    
    Returns:
        Tuple of (DataFrame, list of raw column header names, sanitized filename).
        
    Raises:
        HTTPException: For invalid extension, empty file, oversized file, or malformed CSV.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    clean_filename = sanitize_filename(file.filename)
    
    # 1. Validate file extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .csv files are supported.",
        )

    # 2. Read file content safely with size limit
    file_bytes = await file.read(max_size_bytes + 1)
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed upload size of {max_mb} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes). Please upload a valid CSV.",
        )

    # 3. Decode bytes to string
    csv_text = decode_csv_bytes(file_bytes)

    # Check for empty string or only whitespace
    if not csv_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file contains no data or only whitespace.",
        )

    # 4. Extract raw headers using python csv reader to detect duplicate column names
    raw_columns: List[str] = []
    try:
        header_line = csv_text.strip().splitlines()[0]
        # Basic parsing of header line
        import csv
        reader = csv.reader([header_line])
        raw_columns = next(reader)
    except Exception:
        raw_columns = []

    # 5. Parse into Pandas DataFrame
    try:
        # Use StringIO to parse without touching disk
        string_io = io.StringIO(csv_text)
        df = pd.read_csv(string_io, dtype=str)
        
        # Strip string values initially so whitespace isn't hidden
        if df.empty and len(df.columns) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded CSV contains no valid rows or columns.",
            )

        return df, raw_columns, clean_filename

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains no readable data or header.",
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed CSV: Failed to parse file rows. Details: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process CSV file: {str(e)}",
        )


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame into UTF-8 encoded CSV bytes ready for file download."""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8")
    return csv_buffer.getvalue().encode("utf-8")
