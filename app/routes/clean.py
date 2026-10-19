"""API route for CSV data cleaning and transformation."""

import json
from typing import Optional, Union
import urllib.parse
from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError

from app.cleaning import clean_dataset
from app.schemas import CleaningConfig, CleaningReport, ErrorResponse
from app.services import dataframe_to_csv_bytes, read_uploaded_csv

router = APIRouter(prefix="/api", tags=["Cleaning"])


def parse_cleaning_config(config_str: Optional[str]) -> CleaningConfig:
    """Parse and validate JSON string into CleaningConfig model."""
    if not config_str or not config_str.strip():
        return CleaningConfig()
    try:
        data = json.loads(config_str)
        return CleaningConfig.model_validate(data)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format for cleaning configuration: {str(e)}",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cleaning configuration schema error: {str(e)}",
        )


@router.post(
    "/clean",
    summary="Clean a CSV file and download the cleaned CSV",
    description=(
        "Applies user-selected cleaning rules (deduplication, column removal, missing value strategies, "
        "type conversions, whitespace trimming, formula neutralization). "
        "Returns downloadable CSV by default, or JSON before-and-after report if preview=true."
    ),
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/json": {"schema": {"$ref": "#/components/schemas/CleaningReport"}},
            },
            "description": "Cleaned CSV file attachment or JSON cleaning report",
        },
        400: {"model": ErrorResponse, "description": "Invalid file or cleaning settings"},
        413: {"model": ErrorResponse, "description": "File size exceeds limit"},
    },
)
async def clean_csv(
    file: UploadFile = File(..., description="CSV file to clean"),
    config: Optional[str] = Form(
        None,
        description="Optional JSON string of CleaningConfig"
    ),
    preview: bool = Query(
        False,
        description="If true, returns the JSON CleaningReport with before-and-after comparison instead of CSV file"
    ),
) -> Response:
    """Execute cleaning pipeline on uploaded CSV."""
    cleaning_config = parse_cleaning_config(config)
    df, _, clean_filename = await read_uploaded_csv(file)

    try:
        output_filename = f"cleaned_{clean_filename}"
        cleaned_df, report = clean_dataset(
            df=df,
            config=cleaning_config,
            filename=output_filename,
        )

        if preview:
            # Return JSON report for dashboard preview and comparison
            return Response(
                content=report.model_dump_json(),
                media_type="application/json",
                status_code=status.HTTP_200_OK,
            )

        # Convert to CSV bytes for download
        csv_bytes = dataframe_to_csv_bytes(cleaned_df)
        
        # Include summary metrics in header (URL encoded to avoid invalid header characters)
        summary_payload = {
            "rows_removed": report.rows_removed,
            "columns_removed": report.columns_removed,
            "missing_resolved": report.missing_resolved,
            "duplicates_removed": report.duplicates_before - report.duplicates_after,
            "operations_count": len(report.operations_applied),
        }
        encoded_summary = urllib.parse.quote(json.dumps(summary_payload))

        headers = {
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "X-Cleaning-Summary": encoded_summary,
            "Access-Control-Expose-Headers": "Content-Disposition, X-Cleaning-Summary",
        }

        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers=headers,
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while cleaning the dataset: {str(e)}",
        )


@router.post(
    "/clean/preview",
    response_model=CleaningReport,
    summary="Preview cleaning operations without downloading",
    description="Applies cleaning rules in-memory and returns a before-and-after comparison with the first 10 rows.",
)
async def clean_csv_preview(
    file: UploadFile = File(..., description="CSV file to clean"),
    config: Optional[str] = Form(None, description="Optional JSON string of CleaningConfig"),
) -> CleaningReport:
    """Endpoint explicitly dedicated to previewing cleaning changes before export."""
    cleaning_config = parse_cleaning_config(config)
    df, _, clean_filename = await read_uploaded_csv(file)

    try:
        _, report = clean_dataset(
            df=df,
            config=cleaning_config,
            filename=f"cleaned_{clean_filename}",
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating cleaning preview: {str(e)}",
        )
