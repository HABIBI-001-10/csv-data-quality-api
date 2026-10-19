"""API route for CSV data validation."""

import json
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.schemas import ErrorResponse, ValidationReport, ValidationRules
from app.services import read_uploaded_csv
from app.validators import validate_dataset

router = APIRouter(prefix="/api", tags=["Validation"])


@router.post(
    "/validate",
    response_model=ValidationReport,
    summary="Validate a CSV file against quality rules",
    description="Upload a CSV file and optional validation rules in JSON format to detect data quality errors and warnings.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file, rules, or CSV structure"},
        413: {"model": ErrorResponse, "description": "File size exceeds limit"},
    },
)
async def validate_csv(
    file: UploadFile = File(..., description="CSV file to validate"),
    rules: Optional[str] = Form(
        None,
        description="Optional JSON string of ValidationRules (e.g. required columns, expected types)"
    ),
) -> ValidationReport:
    """Validate uploaded CSV against standard and user-configured quality rules."""
    parsed_rules = ValidationRules()
    if rules and rules.strip():
        try:
            rule_dict = json.loads(rules)
            parsed_rules = ValidationRules.model_validate(rule_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format for validation rules: {str(e)}",
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation rules schema error: {str(e)}",
            )

    df, raw_columns, clean_filename = await read_uploaded_csv(file)
    try:
        report = validate_dataset(
            df,
            rules=parsed_rules,
            filename=clean_filename,
            raw_column_names=raw_columns,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while validating the dataset: {str(e)}",
        )
