import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers():
    from core.security import create_access_token
    token = create_access_token({"sub": "user-1", "email": "u@t.com"})
    return {"Authorization": f"Bearer {token}"}


def _mock_user():
    return {
        "id": "user-1",
        "email": "u@t.com",
        "password_hash": "$2b$12$dummy",
        "first_name": "Test",
        "last_name": "User",
        "company_name": None,
        "profile_image_url": None,
        "role": "1",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "last_login": None,
    }


@pytest.mark.security
class TestSQLInjection:

    def test_sql_injection_in_settings_field(self, client, auth_headers):
        with patch('core.database.execute_query', return_value=[_mock_user()]):
            with patch('api.endpoints.settings.execute_query') as mock_eq:
                with patch('api.endpoints.settings.execute_insert') as mock_ei:
                    mock_eq.return_value = [{
                        "id": "s1", "user_id": "user-1",
                        "theme": "light", "language": "es", "currency": "EUR",
                        "email_notifications": True, "push_notifications": True,
                        "allow_analytics": False,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }]
                    mock_ei.return_value = {
                        "id": "s1", "user_id": "user-1",
                        "theme": "light", "language": "'; DROP TABLE users; --",
                        "currency": "EUR",
                        "email_notifications": True, "push_notifications": True,
                        "allow_analytics": False,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }

                    resp = client.put(
                        "/api/settings",
                        headers=auth_headers,
                        json={"language": "'; DROP TABLE users; --"},
                    )
                    assert resp.status_code == 422

    def test_sql_injection_in_login_email(self, client):
        payload = {
            "email": "' OR '1'='1'; --",
            "password": "password123",
        }
        with patch('api.endpoints.auth.execute_query', return_value=[]):
            resp = client.post("/api/auth/login", json=payload)
            assert resp.status_code in (401, 422)

    def test_sql_injection_in_register_fields(self, client):
        app.state.limiter.reset()
        payload = {
            "email": "legit@test.com",
            "password": "Test1234!Aa",
            "first_name": "Robert'; DROP TABLE users; --",
            "last_name": "Tables",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        }
        user_row = {
            "id": "new-id",
            "email": "legit@test.com",
            "first_name": "Robert'; DROP TABLE users; --",
            "last_name": "Tables",
            "company_name": None,
            "role": "1",
            "is_active": True,
            "profile_image_url": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        with patch('api.endpoints.auth.execute_query', return_value=[]):
            with patch('api.endpoints.auth.execute_insert', return_value=user_row):
                with patch('api.endpoints.auth.create_notification'):
                    resp = client.post("/api/auth/register", json=payload)
                    assert resp.status_code in (201, 200)


@pytest.mark.security
class TestProtectedEndpoints:

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/settings"),
        ("PUT", "/api/settings"),
        ("GET", "/api/contracts"),
        ("GET", "/api/notifications"),
        ("GET", "/api/usage"),
        ("GET", "/api/generated-contracts"),
    ]

    @pytest.mark.parametrize("method,url", PROTECTED_ENDPOINTS)
    def test_protected_endpoints_require_auth(self, client, method, url):
        if method == "GET":
            resp = client.get(url)
        elif method == "PUT":
            resp = client.put(url, json={})
        else:
            resp = client.post(url)

        assert resp.status_code in (401, 403)


@pytest.mark.security
class TestEmailEnumeration:

    @pytest.fixture(autouse=True)
    def _reset_limiter(self):
        try:
            from app import app as _app
            _app.state.limiter.reset()
        except Exception:
            pass

    def test_forgot_password_existing_email(self, client):
        with patch('api.endpoints.auth.execute_query') as mock:
            mock.return_value = [_mock_user()]
            with patch('api.endpoints.auth.send_password_reset_email'):
                with patch('api.endpoints.auth.create_reset_token', return_value="tok"):
                    with patch('api.endpoints.auth.execute_update'):
                        resp = client.post(
                            "/api/auth/forgot-password",
                            json={"email": "existing@test.com"},
                        )
        assert resp.status_code == 200
        body = resp.json()
        assert "Si el correo" in body["message"]

    def test_forgot_password_nonexistent_email(self, client):
        with patch('api.endpoints.auth.execute_query', return_value=[]):
            resp = client.post(
                "/api/auth/forgot-password",
                json={"email": "nonexistent@test.com"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "Si el correo" in body["message"]

    def test_forgot_password_same_response(self, client):
        try:
            from app import app as _app
            _app.state.limiter.reset()
        except Exception:
            pass

        with patch('api.endpoints.auth.execute_query', return_value=[]):
            resp_nonexistent = client.post(
                "/api/auth/forgot-password",
                json={"email": "ghost@test.com"},
            )

        with patch('api.endpoints.auth.execute_query') as mock:
            mock.return_value = [_mock_user()]
            with patch('api.endpoints.auth.send_password_reset_email'):
                with patch('api.endpoints.auth.create_reset_token', return_value="tok"):
                    with patch('api.endpoints.auth.execute_update'):
                        resp_existing = client.post(
                            "/api/auth/forgot-password",
                            json={"email": "real@test.com"},
                        )

        assert resp_nonexistent.json()["message"] == resp_existing.json()["message"]
