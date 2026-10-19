"""API route for CSV profiling."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.profiler import profile_dataset
from app.schemas import ErrorResponse, ProfileReport
from app.services import read_uploaded_csv

router = APIRouter(prefix="/api", tags=["Profiling"])


@router.post(
    "/profile",
    response_model=ProfileReport,
    summary="Profile a CSV file",
    description="Upload a CSV file to compute dataset dimensions, column types, missing values, duplicates, and numeric statistics.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format or empty content"},
        413: {"model": ErrorResponse, "description": "File size exceeds limit"},
    },
)
async def profile_csv(file: UploadFile = File(..., description="CSV file to profile")) -> ProfileReport:
    """Read uploaded CSV and return full dataset profile metadata."""
    df, _, clean_filename = await read_uploaded_csv(file)
    try:
        report = profile_dataset(df, filename=clean_filename)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while profiling the dataset: {str(e)}",
        )
