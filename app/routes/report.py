"""API route for generating and downloading JSON validation reports."""

import json
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError

from app.schemas import ErrorResponse, ValidationRules
from app.services import read_uploaded_csv
from app.validators import validate_dataset

router = APIRouter(prefix="/api", tags=["Report"])


@router.post(
    "/report",
    summary="Generate and download a JSON validation report",
    description="Validates the uploaded CSV file and returns the structured validation report as a downloadable JSON file.",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Downloadable JSON validation report file",
        },
        400: {"model": ErrorResponse, "description": "Invalid file or rules"},
        413: {"model": ErrorResponse, "description": "File size exceeds limit"},
    },
)
async def download_validation_report(
    file: UploadFile = File(..., description="CSV file to validate"),
    rules: Optional[str] = Form(
        None,
        description="Optional JSON string of ValidationRules"
    ),
) -> Response:
    """Validate uploaded CSV and return JSON report as a downloadable file."""
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
            df=df,
            rules=parsed_rules,
            filename=clean_filename,
            raw_column_names=raw_columns,
        )

        json_bytes = report.model_dump_json(indent=2).encode("utf-8")
        base_name = clean_filename.rsplit(".", 1)[0]
        download_filename = f"validation_report_{base_name}.json"

        headers = {
            "Content-Disposition": f'attachment; filename="{download_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }

        return Response(
            content=json_bytes,
            media_type="application/json; charset=utf-8",
            headers=headers,
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the validation report: {str(e)}",
        )
