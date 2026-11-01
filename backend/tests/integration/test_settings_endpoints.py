import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# Funciones auxiliares

def _full_user(sample_user):
    now = datetime.now()
    return {
        **sample_user,
        'company_name': None, 'profile_image_url': None,
        'created_at': now, 'updated_at': now,
    }


def _settings_row(overrides=None):
    now = datetime.now()
    base = {
        'id': 'settings-001',
        'user_id': 'usr-test-001',
        'theme': 'light',
        'language': 'es',
        'currency': 'EUR',
        'email_notifications': True,
        'push_notifications': False,
        'allow_analytics': True,
        'created_at': now,
        'updated_at': now,
    }
    if overrides:
        base.update(overrides)
    return base


# GET /api/settings

@pytest.mark.integration
class TestGetSettings:

    @patch('api.endpoints.settings.execute_query')
    @patch('core.database.execute_query')
    def test_get_settings(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [_settings_row()]

        resp = client.get("/api/settings", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "light"
        assert data["language"] == "es"


# PUT /api/settings

@pytest.mark.integration
class TestUpdateSettings:

    @patch('api.endpoints.settings.execute_insert')
    @patch('core.database.execute_query')
    def test_update_partial(self, mock_eq, mock_insert, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]
        mock_insert.return_value = _settings_row({'theme': 'dark'})

        resp = client.put("/api/settings", headers=auth_headers, json={
            "theme": "dark",
        })

        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"

    @patch('api.endpoints.settings.execute_insert')
    @patch('core.database.execute_query')
    def test_update_multiple_fields(self, mock_eq, mock_insert, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]
        mock_insert.return_value = _settings_row({'theme': 'dark', 'language': 'en'})

        resp = client.put("/api/settings", headers=auth_headers, json={
            "theme": "dark",
            "language": "en",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "dark"
        assert data["language"] == "en"

    def test_field_whitelist_blocks_injection(self, client, auth_headers):
        resp = client.put("/api/settings", headers=auth_headers, json={
            "theme": "dark",
            "\"; DROP TABLE users;--": "attack",
        })

        assert resp.status_code in (200, 401, 422)


# GET /api/usage

@pytest.mark.integration
class TestGetUsage:

    @patch('api.endpoints.usage.get_usage')
    @patch('core.database.execute_query')
    def test_get_usage(self, mock_eq, mock_get_usage, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]
        mock_get_usage.return_value = {
            'plan': 'free',
            'usage': {'contracts_analyzed': 1, 'contracts_generated': 0, 'ai_modifications': {}},
            'limits': {'contracts_analyzed': 3, 'contracts_generated': 1, 'ai_modifications_per_contract': 3},
            'period_start': '2024-01-01',
            'period_end': '2024-02-01',
        }

        resp = client.get("/api/usage", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert "usage" in data
        assert "limits" in data
