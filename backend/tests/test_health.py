import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz_endpoint(client):
    """Verify that /healthz returns 200 with required health metadata."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "storage_mode" in data
    assert "timestamp_utc" in data
    assert "X-Request-ID" in response.headers


def test_api_root_endpoint(client):
    """Verify /api root provides service and documentation links."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["docs_url"] == "/api/docs"
    assert data["health_url"] == "/healthz"
    assert "disclaimer" in data


def test_request_id_middleware(client):
    """Verify custom X-Request-ID propagation."""
    custom_id = "test-request-id-12345"
    response = client.get("/healthz", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
    assert "X-Response-Time-Ms" in response.headers
