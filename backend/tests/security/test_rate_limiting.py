import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from app import app
from core.config import settings


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _mock_db_user():
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "test@test.com",
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
class TestRateLimiting:

    def _reset_limiter(self):
        try:
            app.state.limiter.reset()
        except Exception:
            pass

    def test_login_rate_limit_5_per_min(self, client):
        self._reset_limiter()
        payload = {"email": "nobody@test.com", "password": "wrong"}

        with patch('api.endpoints.auth.execute_query', return_value=[]):
            last_status = None
            for i in range(8):
                resp = client.post("/api/auth/login", json=payload)
                last_status = resp.status_code
                if resp.status_code == 429:
                    break

            assert last_status == 429

    def test_trusted_proxy_separates_forwarded_client_ips(self):
        self._reset_limiter()
        payload = {"email": "nobody@test.com", "password": "wrong"}

        with TestClient(app, raise_server_exceptions=False, client=("172.20.0.10", 50000)) as proxy_client:
            with patch.object(settings, "trusted_proxies", ["172.16.0.0/12"]):
                with patch('api.endpoints.auth.execute_query', return_value=[]):
                    for _ in range(5):
                        resp = proxy_client.post(
                            "/api/auth/login",
                            json=payload,
                            headers={"X-Forwarded-For": "198.51.100.10"},
                        )
                        assert resp.status_code != 429

                    other_client_resp = proxy_client.post(
                        "/api/auth/login",
                        json=payload,
                        headers={"X-Forwarded-For": "198.51.100.11"},
                    )
                    assert other_client_resp.status_code != 429

                    limited_resp = proxy_client.post(
                        "/api/auth/login",
                        json=payload,
                        headers={"X-Forwarded-For": "198.51.100.10"},
                    )
                    assert limited_resp.status_code == 429

    def test_untrusted_client_cannot_spoof_forwarded_for(self):
        self._reset_limiter()
        payload = {"email": "nobody@test.com", "password": "wrong"}

        with TestClient(app, raise_server_exceptions=False, client=("203.0.113.20", 50000)) as direct_client:
            with patch.object(settings, "trusted_proxies", ["172.16.0.0/12"]):
                with patch('api.endpoints.auth.execute_query', return_value=[]):
                    last_status = None
                    for i in range(6):
                        resp = direct_client.post(
                            "/api/auth/login",
                            json=payload,
                            headers={"X-Forwarded-For": f"198.51.100.{i + 1}"},
                        )
                        last_status = resp.status_code

                    assert last_status == 429

    def test_register_rate_limit_3_per_min(self, client):
        self._reset_limiter()
        payload = {
            "email": "new@test.com",
            "password": "Test1234!Aa",
            "first_name": "Test",
            "last_name": "User",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        }

        with patch('api.endpoints.auth.execute_query', return_value=[]):
            with patch('api.endpoints.auth.execute_insert_returning', return_value={"id": "new-id"}):
                last_status = None
                for i in range(6):
                    resp = client.post("/api/auth/register", json=payload)
                    last_status = resp.status_code
                    if resp.status_code == 429:
                        break

                assert last_status == 429

    def test_forgot_password_3_per_hour(self, client):
        self._reset_limiter()
        payload = {"email": "test@test.com"}

        with patch('api.endpoints.auth.execute_query', return_value=[]):
            last_status = None
            for i in range(6):
                resp = client.post("/api/auth/forgot-password", json=payload)
                last_status = resp.status_code
                if resp.status_code == 429:
                    break

            assert last_status == 429

    def test_chat_rate_limit_20_per_min(self, client):
        self._reset_limiter()
        from core.security import create_access_token
        token = create_access_token({"sub": "user-1", "email": "u@t.com"})
        headers = {"Authorization": f"Bearer {token}"}

        with patch('core.database.execute_query') as mock_eq:
            mock_eq.return_value = [_mock_db_user()]
            with patch('api.endpoints.agent.execute_query', return_value=[{"id": "c1", "user_id": "user-1"}]):
                last_status = None
                for i in range(25):
                    resp = client.post(
                        "/api/agent/conversations/c1/chat",
                        headers=headers,
                        json={"message": "hola"},
                    )
                    last_status = resp.status_code
                    if resp.status_code == 429:
                        break

                assert last_status == 429

    def test_upload_rate_limit_10_per_min(self, client):
        self._reset_limiter()
        import io
        from core.security import create_access_token
        token = create_access_token({"sub": "user-1", "email": "u@t.com"})
        headers = {"Authorization": f"Bearer {token}"}

        with patch('core.database.execute_query') as mock_eq:
            mock_eq.return_value = [_mock_db_user()]
            with patch('api.endpoints.contracts.execute_query', return_value=[]):
                with patch('api.endpoints.contracts.can_analyze_contract', return_value=True):
                    last_status = None
                    for i in range(15):
                        f = io.BytesIO(b"contenido")
                        resp = client.post(
                            "/api/contracts/upload",
                            headers=headers,
                            files={"file": ("test.txt", f, "text/plain")},
                        )
                        last_status = resp.status_code
                        if resp.status_code == 429:
                            break

                    assert last_status == 429
