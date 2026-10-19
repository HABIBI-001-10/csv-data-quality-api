"""Integration tests for REST API endpoints using HTTPX and FastAPI TestClient."""

import io
import json
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TRANSPORT = ASGITransport(app=app)
BASE_URL = "http://testserver"


@pytest.mark.anyio
async def test_health_endpoint():
    """Verify GET /health returns 200 OK and valid status info."""
    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.anyio
async def test_dashboard_endpoint():
    """Verify GET / returns 200 OK with HTML content."""
    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.anyio
async def test_profile_api_success():
    """Verify POST /api/profile returns complete profiling metadata."""
    csv_content = b"id,name,score\n1,Alice,90\n2,Bob,\n3,Bob,85\n"
    files = {"file": ("data.csv", csv_content, "text/csv")}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/profile", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 3
        assert data["total_columns"] == 3
        assert len(data["columns"]) == 3
        assert len(data["preview"]) == 3


@pytest.mark.anyio
async def test_profile_api_empty_file():
    """Verify uploading an empty CSV file returns 400 Bad Request."""
    files = {"file": ("empty.csv", b"", "text/csv")}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/profile", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_profile_api_invalid_extension():
    """Verify non-CSV files are rejected with 400 Bad Request."""
    files = {"file": ("data.txt", b"id,name\n1,Alice", "text/plain")}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/profile", files=files)
        assert response.status_code == 400
        assert "unsupported file format" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_profile_api_utf8_bom():
    """Verify UTF-8-with-BOM encoded CSV is seamlessly supported."""
    csv_bytes = "\ufeffid,name\n1,Alice\n2,Bob\n".encode("utf-8")
    files = {"file": ("bom.csv", csv_bytes, "text/csv")}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/profile", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["column_names"][0] == "id"  # BOM must not pollute the first column name


@pytest.mark.anyio
async def test_validate_api_with_rules():
    """Verify POST /api/validate flags errors for missing columns and invalid emails."""
    csv_content = b"id,user_email,age\n1,valid@example.com,25\n2,notanemail,thirty\n"
    rules = {
        "required_columns": ["id", "user_email", "department"],
        "email_columns": ["user_email"],
        "expected_types": {"age": "integer"},
    }
    files = {"file": ("users.csv", csv_content, "text/csv")}
    data = {"rules": json.dumps(rules)}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/validate", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["summary"]["status"] == "errors_found"
        assert result["summary"]["error_count"] >= 3

        issue_types = [i["issue_type"] for i in result["issues"]]
        assert "missing_required_column" in issue_types
        assert "invalid_email" in issue_types
        assert "invalid_numeric" in issue_types


@pytest.mark.anyio
async def test_validate_api_invalid_rules_json():
    """Verify invalid JSON in rules parameter returns 400 Bad Request."""
    files = {"file": ("test.csv", b"id,name\n1,A", "text/csv")}
    data = {"rules": "{bad-json"}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/validate", files=files, data=data)
        assert response.status_code == 400
        assert "invalid json" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_clean_api_download_csv():
    """Verify POST /api/clean downloads cleaned CSV and sets X-Cleaning-Summary header."""
    csv_content = b"first name,score\n  Alice  ,90\nBob,80\nBob,80\n"
    config = {
        "drop_duplicates": True,
        "trim_whitespace": True,
        "standardize_column_names": True,
    }
    files = {"file": ("data.csv", csv_content, "text/csv")}
    data = {"config": json.dumps(config)}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/clean", files=files, data=data)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert "X-Cleaning-Summary" in response.headers

        # Verify cleaned CSV contents
        cleaned_text = response.text
        assert "first_name,score" in cleaned_text  # standardized header
        assert "Alice" in cleaned_text
        # Duplicate row Bob,80 should only appear once
        assert cleaned_text.count("Bob,80") == 1


@pytest.mark.anyio
async def test_clean_api_preview_mode():
    """Verify POST /api/clean with preview=true returns JSON before-and-after comparison."""
    csv_content = b"id,val\n1,a\n2,\n"
    config = {"missing_value_strategy": "drop_rows"}
    files = {"file": ("preview.csv", csv_content, "text/csv")}
    data = {"config": json.dumps(config)}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/clean?preview=true", files=files, data=data)
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        report = response.json()
        assert report["rows_before"] == 2
        assert report["rows_after"] == 1
        assert report["rows_removed"] == 1


@pytest.mark.anyio
async def test_report_api_download_json():
    """Verify POST /api/report returns downloadable JSON validation report."""
    csv_content = b"col1,col2\nval1,\n"
    files = {"file": ("sample.csv", csv_content, "text/csv")}

    async with AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        response = await client.post("/api/report", files=files)
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        # Parse downloaded content
        report_data = json.loads(response.text)
        assert "summary" in report_data
        assert "issues" in report_data
        assert report_data["total_rows"] == 1
