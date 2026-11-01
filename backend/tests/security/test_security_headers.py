import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.security
class TestCORS:

    def test_cors_allowed_origin(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_allowed_origin_includes_credentials(self, client):
        resp = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_preflight_allowed_origin(self, client):
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "POST" in resp.headers.get("access-control-allow-methods", "")
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_blocked_origin(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "http://evil.com"


@pytest.mark.security
class TestSecurityHeaders:

    def test_x_content_type_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_xss_protection(self, client):
        resp = client.get("/health")
        assert "1" in resp.headers.get("x-xss-protection", "")

    def test_referrer_policy(self, client):
        resp = client.get("/health")
        assert resp.headers.get("referrer-policy") is not None
