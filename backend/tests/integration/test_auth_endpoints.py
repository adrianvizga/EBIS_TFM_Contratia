import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from core.security import create_access_token, create_refresh_token, create_reset_token, hash_password


# Funciones auxiliares

def _user_db_row(overrides=None):
    now = datetime.now()
    base = {
        'id': 'usr-test-001',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'company_name': None,
        'role': '1',
        'is_active': True,
        'profile_image_url': None,
        'password_hash': hash_password('Test1234'),
        'created_at': now,
        'updated_at': now,
    }
    if overrides:
        base.update(overrides)
    return base


# POST /api/auth/register

@pytest.mark.integration
class TestRegister:

    @patch('api.endpoints.auth.create_notification')
    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    def test_register_success(self, mock_query, mock_insert, mock_notif, client):
        mock_query.return_value = []  # email no existe
        now = datetime.now()
        mock_insert.side_effect = [
            {
                'id': 'new-uuid', 'email': 'new@example.com',
                'first_name': 'Nuevo', 'last_name': 'Usuario',
                'company_name': None, 'role': '1', 'is_active': True,
                'profile_image_url': None,
                'created_at': now, 'updated_at': now,
            },
            None,
        ]
        mock_notif.return_value = True

        resp = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "Test1234",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" not in data
        set_cookie = resp.headers.get("set-cookie", "")
        assert "contratia_refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert data["user"]["email"] == "new@example.com"

    @patch('api.endpoints.auth.execute_query')
    def test_register_duplicate_email(self, mock_query, client):
        mock_query.return_value = [{'id': 'existing-user'}]

        resp = client.post("/api/auth/register", json={
            "email": "existing@example.com",
            "password": "Test1234",
            "first_name": "Test",
            "last_name": "User",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        })

        assert resp.status_code == 409

    def test_register_without_explicit_consent_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com", "password": "Test1234",
            "first_name": "Test", "last_name": "User",
        })
        assert resp.status_code == 422

    def test_register_with_rejected_consent_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com", "password": "Test1234",
            "first_name": "Test", "last_name": "User",
            "terms_accepted": False, "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        })
        assert resp.status_code == 422

    def test_register_with_stale_legal_version_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com", "password": "Test1234",
            "first_name": "Test", "last_name": "User",
            "terms_accepted": True, "terms_version": "terms-old",
            "privacy_version": "privacy-2026-06-20",
        })
        assert resp.status_code == 422

    def test_register_weak_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "test1234",  # sin mayúscula
            "first_name": "Test",
            "last_name": "User",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        })

        assert resp.status_code == 422

    @patch('api.endpoints.auth.create_notification')
    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    def test_register_short_password(self, mock_query, mock_insert, mock_notif, client):
        resp = client.post("/api/auth/register", json={
            "email": "a@b.com",
            "password": "Te1",
            "first_name": "A",
            "last_name": "B",
            "terms_accepted": True,
            "terms_version": "terms-2026-06-20",
            "privacy_version": "privacy-2026-06-20",
        })

        assert resp.status_code == 422


# POST /api/auth/login

@pytest.mark.integration
class TestLogin:

    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    def test_login_success(self, mock_query, mock_insert, client):
        user_row = _user_db_row()
        mock_query.return_value = [user_row]
        mock_insert.return_value = None  # session insert

        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test1234",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" not in data
        set_cookie = resp.headers.get("set-cookie", "")
        assert "contratia_refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie

    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    def test_login_remember_me_sets_persistent_cookie(self, mock_query, mock_insert, client):
        user_row = _user_db_row()
        mock_query.return_value = [user_row]
        mock_insert.return_value = None

        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test1234",
            "remember_me": True,
        })

        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "contratia_refresh_token=" in set_cookie
        assert "Max-Age=" in set_cookie

    @patch('api.endpoints.auth.execute_query')
    def test_login_wrong_password(self, mock_query, client):
        user_row = _user_db_row()
        mock_query.return_value = [user_row]

        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPass1",
        })

        assert resp.status_code == 401

    @patch('api.endpoints.auth.execute_query')
    def test_login_nonexistent_email(self, mock_query, client):
        mock_query.return_value = []

        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "Test1234",
        })

        assert resp.status_code == 401

    @patch('api.endpoints.auth.execute_query')
    def test_login_inactive_account(self, mock_query, client):
        user_row = _user_db_row({'is_active': False})
        mock_query.return_value = [user_row]

        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test1234",
        })

        assert resp.status_code == 403


# POST /api/auth/refresh

@pytest.mark.integration
class TestRefreshToken:

    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_delete')
    @patch('api.endpoints.auth.execute_query')
    def test_refresh_token_success(self, mock_query, mock_delete, mock_insert, client):
        refresh = create_refresh_token({"sub": "usr-test-001", "email": "t@t.com"})
        mock_query.return_value = [{'id': 'session-1'}]  # sesión existe
        mock_delete.return_value = 1
        mock_insert.return_value = None

        resp = client.post("/api/auth/refresh", cookies={"contratia_refresh_token": refresh})

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "contratia_refresh_token=" in resp.headers.get("set-cookie", "")
        mock_delete.assert_called_once()
        mock_insert.assert_called_once()

    def test_refresh_token_expired(self, client):
        refresh = create_refresh_token(
            {"sub": "usr-test-001", "email": "t@t.com"},
            expires_delta=timedelta(seconds=-1),
        )

        resp = client.post("/api/auth/refresh", cookies={"contratia_refresh_token": refresh})
        assert resp.status_code == 401

    @patch('api.endpoints.auth.execute_query')
    def test_refresh_token_no_session(self, mock_query, client):
        refresh = create_refresh_token({"sub": "usr-test-001", "email": "t@t.com"})
        mock_query.return_value = []  # sesión borrada

        resp = client.post("/api/auth/refresh", cookies={"contratia_refresh_token": refresh})
        assert resp.status_code == 401


# GET /api/auth/me

@pytest.mark.integration
class TestGetMe:

    @patch('core.database.execute_query')
    def test_get_me(self, mock_eq, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq.return_value = [full_user]

        resp = client.get("/api/auth/me", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    def test_get_me_no_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 403


# PUT /api/auth/me

@pytest.mark.integration
class TestUpdateMe:

    @patch('core.database.execute_query')
    @patch('api.endpoints.auth.execute_transaction')
    def test_update_me(self, mock_transaction, mock_eq, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq.return_value = [full_user]

        updated_user = {**full_user, 'first_name': 'Nuevo'}
        mock_transaction.return_value = [updated_user, None]

        resp = client.put("/api/auth/me", headers=auth_headers, json={
            "first_name": "Nuevo",
        })

        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Nuevo"


# PUT /api/auth/change-password

@pytest.mark.integration
class TestChangePassword:

    @patch('core.database.execute_query')
    @patch('api.endpoints.auth.execute_query')
    @patch('api.endpoints.auth.execute_update')
    @patch('api.endpoints.auth.execute_delete')
    @patch('api.endpoints.auth.create_notification')
    def test_change_password_success(self, mock_notif, mock_del, mock_upd, mock_eq_endpoint, mock_eq_auth, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = [{'password_hash': hash_password('OldPass1')}]
        mock_upd.return_value = 1
        mock_del.return_value = 1
        mock_notif.return_value = True

        resp = client.put("/api/auth/change-password", headers=auth_headers, json={
            "current_password": "OldPass1",
            "new_password": "NewPass1",
        })

        assert resp.status_code == 200

    @patch('core.database.execute_query')
    @patch('api.endpoints.auth.execute_query')
    def test_change_password_wrong_current(self, mock_eq_endpoint, mock_eq_auth, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = [{'password_hash': hash_password('RealPass1')}]

        resp = client.put("/api/auth/change-password", headers=auth_headers, json={
            "current_password": "WrongCurrent1",
            "new_password": "NewPass1",
        })

        assert resp.status_code == 400

    @patch('core.database.execute_query')
    def test_change_password_weak_new(self, mock_eq, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq.return_value = [full_user]

        resp = client.put("/api/auth/change-password", headers=auth_headers, json={
            "current_password": "OldPass1",
            "new_password": "weak",
        })
        assert resp.status_code == 422


# POST /api/auth/forgot-password

@pytest.mark.integration
class TestForgotPassword:

    @patch('api.endpoints.auth.send_password_reset_email', new_callable=AsyncMock)
    @patch('api.endpoints.auth.execute_query')
    def test_forgot_password_existing(self, mock_query, mock_email, client):
        mock_query.return_value = [{'id': 'usr-1', 'email': 'a@b.com', 'first_name': 'Test'}]
        mock_email.return_value = True

        resp = client.post("/api/auth/forgot-password", json={"email": "a@b.com"})

        assert resp.status_code == 200
        assert "registrado" in resp.json()["message"]

    @patch('api.endpoints.auth.execute_query')
    def test_forgot_password_nonexistent(self, mock_query, client):
        mock_query.return_value = []

        resp = client.post("/api/auth/forgot-password", json={"email": "nobody@abc.com"})

        assert resp.status_code == 200
        assert "registrado" in resp.json()["message"]


# POST /api/auth/reset-password

@pytest.mark.integration
class TestResetPassword:

    @patch('api.endpoints.auth.create_notification')
    @patch('api.endpoints.auth.execute_delete')
    @patch('api.endpoints.auth.execute_update')
    @patch('api.endpoints.auth.execute_query')
    def test_reset_password_valid(self, mock_query, mock_upd, mock_del, mock_notif, client):
        token = create_reset_token('usr-1', 'a@b.com')
        mock_query.return_value = [{'id': 'usr-1'}]
        mock_upd.return_value = 1
        mock_del.return_value = 1
        mock_notif.return_value = True

        resp = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "Nuevo1234",
        })

        assert resp.status_code == 200

    def test_reset_password_expired(self, client):
        import jwt
        from core.config import settings
        payload = {
            "sub": "usr-1", "email": "a@b.com", "type": "reset",
            "exp": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        resp = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "Nuevo1234",
        })

        assert resp.status_code == 400


# DELETE /api/auth/delete-account

@pytest.mark.integration
class TestDeleteAccount:

    @patch('core.database.execute_query')
    @patch('api.endpoints.auth.execute_delete')
    def test_delete_account_correct_email(self, mock_del, mock_eq, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq.side_effect = [
            [full_user],  # get_current_user
            [],           # contracts query (for file cleanup)
        ]
        mock_del.return_value = 1

        resp = client.request("DELETE", "/api/auth/delete-account",
                              headers=auth_headers,
                              json={"email": "test@example.com"})

        assert resp.status_code == 200

    @patch('core.database.execute_query')
    def test_delete_account_wrong_email(self, mock_eq, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {
            **sample_user,
            'company_name': None, 'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }
        mock_eq.return_value = [full_user]

        resp = client.request("DELETE", "/api/auth/delete-account",
                              headers=auth_headers,
                              json={"email": "wrong@example.com"})

        assert resp.status_code == 400


# POST /api/auth/logout

@pytest.mark.integration
class TestLogout:

    @patch('api.endpoints.auth.execute_delete')
    def test_logout_clears_sessions(self, mock_del, client, auth_headers):
        mock_del.return_value = 1

        resp = client.post(
            "/api/auth/logout",
            headers=auth_headers,
            cookies={"contratia_refresh_token": "refresh-token"},
        )

        assert resp.status_code == 200
        mock_del.assert_called_once()
        assert "contratia_refresh_token=" in resp.headers.get("set-cookie", "")


# POST /api/auth/google-login

@pytest.mark.integration
class TestGoogleLogin:

    @patch('api.endpoints.auth.create_notification')
    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    @patch('api.endpoints.auth.id_token')
    def test_google_login_new_user(self, mock_id_token, mock_query, mock_insert, mock_notif, client):
        mock_id_token.verify_oauth2_token.return_value = {
            'iss': 'accounts.google.com',
            'email': 'googleuser@gmail.com',
            'given_name': 'Google',
            'family_name': 'User',
            'picture': 'https://lh3.google.com/photo',
        }
        mock_query.return_value = []  # user no existe
        now = datetime.now()
        mock_insert.side_effect = [
            {
                'id': 'new-google-uid', 'email': 'googleuser@gmail.com',
                'first_name': 'Google', 'last_name': 'User',
                'company_name': None, 'role': '1', 'is_active': True,
                'profile_image_url': 'https://lh3.google.com/photo',
                'created_at': now, 'updated_at': now,
            },
            None,
        ]

        resp = client.post("/api/auth/google-login", json={
            "token": "fake-google-token", "terms_accepted": True,
            "terms_version": "terms-2026-06-20", "privacy_version": "privacy-2026-06-20",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "googleuser@gmail.com"

    @patch('api.endpoints.auth.execute_query', return_value=[])
    @patch('api.endpoints.auth.id_token')
    def test_google_signup_without_consent_is_rejected(self, mock_id_token, mock_query, client):
        mock_id_token.verify_oauth2_token.return_value = {
            'iss': 'accounts.google.com', 'email': 'new@gmail.com',
            'given_name': 'New', 'family_name': 'User',
        }
        resp = client.post("/api/auth/google-login", json={"token": "fake-google-token"})
        assert resp.status_code == 422

    @patch('api.endpoints.auth.create_notification')
    @patch('api.endpoints.auth.execute_insert')
    @patch('api.endpoints.auth.execute_query')
    @patch('api.endpoints.auth.id_token')
    def test_google_login_existing_user(self, mock_id_token, mock_query, mock_insert, mock_notif, client):
        mock_id_token.verify_oauth2_token.return_value = {
            'iss': 'accounts.google.com',
            'email': 'existing@gmail.com',
            'given_name': 'Ex',
            'family_name': 'User',
            'picture': 'https://photo.url',
        }
        now = datetime.now()
        mock_query.return_value = [{
            'id': 'existing-uid', 'email': 'existing@gmail.com',
            'password_hash': 'xxx', 'first_name': 'Ex', 'last_name': 'User',
            'company_name': None, 'role': '1', 'is_active': True,
            'profile_image_url': None,
            'created_at': now, 'updated_at': now,
        }]
        mock_insert.return_value = None  # session

        resp = client.post("/api/auth/google-login", json={"token": "fake-google-token"})

        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @patch('api.endpoints.auth.id_token')
    def test_google_login_invalid_token(self, mock_id_token, client):
        mock_id_token.verify_oauth2_token.side_effect = ValueError("Invalid token")

        resp = client.post("/api/auth/google-login", json={"token": "bad-token"})

        assert resp.status_code == 400
