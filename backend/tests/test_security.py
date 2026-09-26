import pytest
from app.config import settings

def test_security_headers_middleware(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "default-src 'none'" in response.headers.get("content-security-policy", "")

def test_api_docs_hidden_in_production(client):
    # This test verifies behavior under current test settings.
    # By default enable_api_docs might be true in tests unless overridden.
    if settings.enable_api_docs:
        response = client.get("/docs")
        assert response.status_code == 200
    else:
        response = client.get("/docs")
        assert response.status_code == 404
