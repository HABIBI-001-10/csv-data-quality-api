"""Main FastAPI application module.

Configures:
- Application lifecycle and metadata
- REST API route registration
- Static asset serving and template rendering
- Global exception handling and JSON error responses
- Health check endpoint
"""

import os
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.routes.clean import router as clean_router
from app.routes.profile import router as profile_router
from app.routes.report import router as report_router
from app.routes.validate import router as validate_router
from app.schemas import ErrorResponse, HealthResponse

# Application base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Initialize FastAPI app
app = FastAPI(
    title="CSV Data Validation and Cleaning API",
    description=(
        "Production-minded REST API for uploading, profiling, validating, "
        "and cleaning CSV datasets with configurable quality rules and safe exports."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for development and cross-origin consumer flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Register API routers
app.include_router(profile_router)
app.include_router(validate_router)
app.include_router(clean_router)
app.include_router(report_router)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Return uniform JSON error response for standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPError",
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return friendly structured error for request validation failures."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request parameter validation failed.",
            details=exc.errors(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected internal server errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected server error occurred. Please verify your input or check server logs.",
            details=str(exc) if os.getenv("DEBUG", "False").lower() == "true" else None,
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service Health Check",
    description="Returns the operational status, application name, and version.",
)
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(
        status="healthy",
        app_name="CSV Data Validation and Cleaning API",
        version=__version__,
    )


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Frontend"],
    summary="Dashboard Interface",
    description="Serves the web dashboard for interactive CSV profiling, validation, and cleaning.",
)
async def serve_dashboard(request: Request):
    """Serve the single-page application dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_version": __version__},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
