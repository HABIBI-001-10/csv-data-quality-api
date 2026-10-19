# CSV Data Validation and Cleaning API

A production-minded, beginner-friendly REST API and interactive web studio built with **FastAPI**, **Pandas**, and **Pydantic**. This application allows users to upload CSV files, profile dataset structures and summary statistics, detect data-quality anomalies against configurable rules, apply non-destructive data cleaning operations, and safely export cleaned CSV files and JSON validation reports.

---

## Table of Contents

1. [Project Overview & Architecture](#project-overview--architecture)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Installation & Setup (Windows & Cross-Platform)](#installation--setup)
6. [Running the Application](#running-the-application)
7. [API Endpoints & Documentation](#api-endpoints--documentation)
8. [Sample Input & Output](#sample-input--output)
9. [Automated Testing](#automated-testing)
10. [Security & Reliability Safeguards](#security--reliability-safeguards)
11. [Deployment Guide](#deployment-guide)
12. [Known Limitations & Future Improvements](#known-limitations--future-improvements)

---

## 1. Project Overview & Architecture

Data quality issues—such as missing values, duplicated entries, malformed dates, unstandardized column headers, and injection vulnerabilities—plague real-world data pipelines. This project addresses these challenges with a clear separation of concerns:

- **Service Layer (`app/services.py`)**: Validates file types, handles encoding fallbacks (UTF-8, UTF-8-BOM, Latin-1), validates file sizes up to 10 MB, and prevents filename traversal.
- **Profiling Engine (`app/profiler.py`)**: Computes structural dimensions, per-column missing percentages, duplicate row counts, unique values, numeric percentiles, and 10-row previews without saving files permanently to disk.
- **Validation Engine (`app/validators.py`)**: Distinguishes between **Errors** (missing required columns, unparseable data types) and **Warnings** (missing values, duplicate rows, empty columns). Never makes silent assumptions about email or date semantics unless explicitly configured.
- **Cleaning Engine (`app/cleaning.py`)**: Provides user-controlled transformations including deduplication, whitespace trimming, column dropping, configurable missing value imputation (leave, drop, fill custom, mean, median, mode), type casting, column name standardization, and formula injection sanitization.
- **Interactive UI (`app/templates/index.html`, `app/static/`)**: A responsive single-page dashboard featuring drag-and-drop upload, summary metric cards, interactive rule configuration, and before-and-after change diffs.

---

## 2. Key Features

- **CSV Upload & Ingestion**:
  - Validates `.csv` extensions and rejects empty or malformed files.
  - Multi-encoding resilience: UTF-8, UTF-8-with-BOM, Latin-1, and CP1252.
  - Memory-safe streaming and size enforcement (default 10 MB limit).
- **Automated Data Profiling**:
  - Total rows and columns.
  - Inferred Pandas data types.
  - Missing value counts and percentages per column.
  - Duplicate row detection and percentage.
  - Numeric summary statistics: Min, 25%, Median, Mean, 75%, Max.
  - Interactive 10-row dataset preview.
- **Configurable Data Validation**:
  - Required columns enforcement.
  - Email format validation (RFC 5322 regex).
  - Date format parsing (ISO standard or explicit custom strftime format).
  - Integer and float validity checks.
  - Duplicate column name detection from raw headers.
  - Clear differentiation between errors and warnings with 1-indexed row numbers.
- **Configurable Data Cleaning**:
  - Deduplication across all columns or selected subsets.
  - Selective column removal.
  - Missing value strategies: `leave`, `drop_rows`, `fill_value`, `fill_mean`, `fill_median`, `fill_mode`.
  - Type casting with error coercion.
  - Whitespace trimming across textual data.
  - Column name standardization into `snake_case`.
  - CSV formula injection protection (escapes `=`, `+`, `-`, `@`).
- **Comprehensive Exports**:
  - Download cleaned CSV with original column order preserved.
  - Download structured validation audit reports as JSON.
  - Real-time before-and-after comparison view with an itemized operations log.

---

## 3. Technology Stack

- **Python 3.12+**
- **FastAPI**: Modern, fast web framework for REST API development.
- **Uvicorn**: High-performance ASGI web server.
- **Pandas (3.0+) & NumPy**: High-performance in-memory dataset manipulation and profiling.
- **Pydantic (v2)**: Strict request and configuration validation.
- **Jinja2**: Server-side template rendering for the frontend dashboard.
- **Pytest & HTTPX**: Automated unit and asynchronous integration testing.
- **Vanilla HTML5, CSS3, & Modern JavaScript**: Clean, responsive, and accessible UI without heavy frontend framework dependencies.

---

## 4. Project Structure

```text
csv-data-quality-api/
├── app/
│   ├── __init__.py          # Application package and version metadata
│   ├── main.py              # FastAPI app initialization, middleware, routes, exception handlers
│   ├── schemas.py           # Pydantic models for profiling, validation, and cleaning
│   ├── validators.py        # Quality inspection engine (errors vs warnings)
│   ├── cleaning.py          # Configurable transformation and sanitization engine
│   ├── profiler.py          # Summary statistics and metadata extraction
│   ├── services.py          # Safe file parsing, encoding decoding, and export helpers
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── profile.py       # POST /api/profile
│   │   ├── validate.py      # POST /api/validate
│   │   ├── clean.py         # POST /api/clean & POST /api/clean/preview
│   │   └── report.py        # POST /api/report
│   ├── static/
│   │   ├── style.css        # Clean, accessible dashboard styling
│   │   └── script.js        # Dynamic DOM handling and API integration
│   └── templates/
│       └── index.html       # Single-page dashboard interface
├── tests/
│   ├── test_validators.py   # Unit tests for quality validation logic
│   ├── test_cleaning.py     # Unit tests for transformations and formula escaping
│   ├── test_profiler.py     # Unit tests for metrics and statistical summary
│   └── test_api.py          # Integration tests for all REST endpoints using HTTPX
├── sample_data/
│   └── messy_data.csv       # Demonstration dataset with typical real-world defects
├── .env.example             # Template for environment configuration
├── .gitignore               # Standard exclusions for Python and environments
├── requirements.txt         # Pinned production dependencies
└── README.md                # Comprehensive documentation
```

---

## 5. Installation & Setup

### Prerequisites

- Python 3.12 or higher installed. Verify with:
  ```powershell
  python --version
  ```

### Step 1: Clone or Navigate to the Repository

```powershell
cd c:\Users\cozme\Desktop\pythonproject
```

### Step 2: Set Up Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Windows (CMD)
.venv\Scripts\activate.bat

# Activate on macOS/Linux
source .venv/bin/activate
```

### Step 3: Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Running the Application

### Start Development Server

Run the following command in the project root:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once started:
- **Interactive Web Dashboard**: Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. API Endpoints & Documentation

| Method | Endpoint | Description | Request Type | Response Type |
|---|---|---|---|---|
| `GET` | `/` | Serves the web dashboard interface | N/A | `text/html` |
| `GET` | `/health` | Service health status check | N/A | `application/json` |
| `POST` | `/api/profile` | Profiles an uploaded CSV file | `multipart/form-data` (`file`) | `application/json` (`ProfileReport`) |
| `POST` | `/api/validate` | Validates CSV against quality rules | `multipart/form-data` (`file`, optional `rules`) | `application/json` (`ValidationReport`) |
| `POST` | `/api/clean` | Applies cleaning rules and downloads CSV | `multipart/form-data` (`file`, optional `config`) | `text/csv` (or JSON if `preview=true`) |
| `POST` | `/api/clean/preview` | Returns before/after summary without downloading | `multipart/form-data` (`file`, optional `config`) | `application/json` (`CleaningReport`) |
| `POST` | `/api/report` | Generates and downloads JSON validation report | `multipart/form-data` (`file`, optional `rules`) | `application/json` (attachment) |

### cURL Examples

#### 1. Profile a CSV
```bash
curl -X POST "http://127.0.0.1:8000/api/profile" \
     -F "file=@sample_data/messy_data.csv"
```

#### 2. Validate with Rules
```bash
curl -X POST "http://127.0.0.1:8000/api/validate" \
     -F "file=@sample_data/messy_data.csv" \
     -F 'rules={"required_columns":["Full Name","User Email!"],"email_columns":["User Email!"],"expected_types":{"Age (Years)":"integer"}}'
```

#### 3. Clean and Download CSV
```bash
curl -X POST "http://127.0.0.1:8000/api/clean" \
     -F "file=@sample_data/messy_data.csv" \
     -F 'config={"drop_duplicates":true,"trim_whitespace":true,"standardize_column_names":true,"sanitize_formulas":true}' \
     --output cleaned_data.csv
```

---

## 8. Sample Input & Output

### Input (`sample_data/messy_data.csv`)
```csv
Full Name,User Email!,Age (Years),Registration Date,Account Balance ($),Department
  Alice Johnson  ,alice.johnson@example.com,29,2023-01-15,1450.50,Engineering
Bob Smith,bob.smith-at-domain.com,34,2022-11-05,2300.00,Marketing
Charlie Brown,charlie@brown.org,unknown,2023-02-30,-120.00,Design
Diana Prince,diana.prince@wonder.com,28,2021-08-19,5400.75,Engineering
Diana Prince,diana.prince@wonder.com,28,2021-08-19,5400.75,Engineering
...
```

### Sample Validation Report Output (`POST /api/validate`)
```json
{
  "filename": "messy_data.csv",
  "total_rows": 13,
  "total_columns": 6,
  "summary": {
    "total_issues": 9,
    "error_count": 5,
    "warning_count": 4,
    "status": "errors_found"
  },
  "issues": [
    {
      "id": "dup-row-6",
      "column": null,
      "row": 6,
      "issue_type": "duplicate_row",
      "severity": "warning",
      "message": "Row 6 is an exact duplicate of an earlier record."
    },
    {
      "id": "invalid-email-User Email!-3",
      "column": "User Email!",
      "row": 3,
      "issue_type": "invalid_email",
      "severity": "error",
      "message": "Value 'bob.smith-at-domain.com' in column 'User Email!' at row 3 is not a valid email address.",
      "sample_value": "bob.smith-at-domain.com"
    },
    {
      "id": "invalid-int-Age (Years)-4",
      "column": "Age (Years)",
      "row": 4,
      "issue_type": "invalid_numeric",
      "severity": "error",
      "message": "Value 'unknown' in column 'Age (Years)' at row 4 cannot be parsed as an integer.",
      "sample_value": "unknown"
    }
  ]
}
```

---

## 9. Automated Testing

The project includes an end-to-end test suite testing unit algorithms and REST endpoints.

Run all tests with:
```powershell
python -m pytest -v
```

Expected test result:
```text
tests/test_api.py::test_health_endpoint[asyncio] PASSED
tests/test_api.py::test_dashboard_endpoint[asyncio] PASSED
tests/test_api.py::test_profile_api_success[asyncio] PASSED
tests/test_api.py::test_profile_api_empty_file[asyncio] PASSED
tests/test_api.py::test_profile_api_invalid_extension[asyncio] PASSED
tests/test_api.py::test_profile_api_utf8_bom[asyncio] PASSED
tests/test_api.py::test_validate_api_with_rules[asyncio] PASSED
tests/test_api.py::test_validate_api_invalid_rules_json[asyncio] PASSED
tests/test_api.py::test_clean_api_download_csv[asyncio] PASSED
tests/test_api.py::test_clean_api_preview_mode[asyncio] PASSED
tests/test_api.py::test_report_api_download_json[asyncio] PASSED
tests/test_cleaning.py::test_standardize_column_names PASSED
tests/test_cleaning.py::test_formula_injection_sanitization PASSED
tests/test_cleaning.py::test_clean_deduplication PASSED
tests/test_cleaning.py::test_clean_drop_columns PASSED
tests/test_cleaning.py::test_clean_trim_whitespace PASSED
tests/test_cleaning.py::test_clean_missing_drop_rows PASSED
tests/test_cleaning.py::test_clean_missing_fill_strategies PASSED
tests/test_cleaning.py::test_clean_type_conversion PASSED
tests/test_profiler.py::test_sanitize_helpers PASSED
tests/test_profiler.py::test_profile_basic_dataset PASSED
tests/test_profiler.py::test_profile_empty_dataset PASSED
tests/test_profiler.py::test_profile_all_missing_column PASSED
tests/test_validators.py::test_validate_required_columns PASSED
tests/test_validators.py::test_validate_duplicate_columns PASSED
tests/test_validators.py::test_validate_empty_columns PASSED
tests/test_validators.py::test_validate_duplicate_rows PASSED
tests/test_validators.py::test_validate_missing_values PASSED
tests/test_validators.py::test_validate_numeric_column PASSED
tests/test_validators.py::test_validate_date_column PASSED
tests/test_validators.py::test_validate_email_column PASSED
tests/test_validators.py::test_validate_full_dataset_report PASSED

============================= 32 passed in ~1s ==============================
```

---

## 10. Security & Reliability Safeguards

- **No Code Execution**: Uploaded files are exclusively parsed as tabular data. No arbitrary code evaluation (`eval`, `exec`) is executed.
- **Path Traversal Protection**: Filenames extracted from uploads are stripped of directory structures using `os.path.basename` and sanitized via regular expressions.
- **CSV Formula Injection Defense**: When exporting cleaned CSV data, cells starting with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with a leading single quote (`'`), preventing malicious spreadsheet macros from executing in Microsoft Excel or LibreOffice Calc.
- **Memory Protection**: File uploads are capped at 10 MB and read directly into memory as `io.StringIO` without writing intermediate files to disk.
- **No Silent Modification**: The cleaning engine operates on an explicit copy of the DataFrame; original inputs are never modified.

---

## 11. Deployment Guide

### Option 1: Render / Railway / Fly.io

1. **Procfile** (or start command):
   ```text
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
2. **Environment Variables**:
   Set `APP_ENV=production` and `DEBUG=False`.
3. Connect your GitHub repository to trigger automatic builds via `requirements.txt`.

### Option 2: Docker Containerization

Create a `Dockerfile` in the root directory:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t csv-quality-api .
docker run -p 8000:8000 csv-quality-api
```

---

## 12. Known Limitations & Future Improvements

- **File Size**: Designed for in-memory datasets up to ~50 MB. For multi-gigabyte datasets, chunked processing with Polars or DuckDB is recommended.
- **Encoding Detection**: Fallbacks cover UTF-8, UTF-8-BOM, Latin-1, and CP1252. Unusual legacy Asian encodings (e.g., Shift-JIS) may require `chardet`.
- **Validation Scope**: Email checking uses standard RFC regex syntax and checks syntax only (does not verify DNS MX records).
- **Future Enhancements**:
  - Parquet and JSON file ingestion support.
  - Regex-based custom pattern validation rules.
  - Anomaly and outlier detection using Z-score or IQR thresholds.
