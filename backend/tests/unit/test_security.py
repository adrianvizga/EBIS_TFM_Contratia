import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

pytestmark = pytest.mark.unit


class TestPasswordHashing:

    def test_hash_password_returns_bcrypt(self):
        from core.security import hash_password
        hashed = hash_password("TestPassword1")
        assert hashed.startswith("$2b$")

    def test_hash_password_different_each_time(self):
        from core.security import hash_password
        h1 = hash_password("SamePass1")
        h2 = hash_password("SamePass1")
        assert h1 != h2

    def test_verify_password_correct(self):
        from core.security import hash_password, verify_password
        hashed = hash_password("CorrectPass1")
        assert verify_password("CorrectPass1", hashed) is True

    def test_verify_password_incorrect(self):
        from core.security import hash_password, verify_password
        hashed = hash_password("CorrectPass1")
        assert verify_password("WrongPass1", hashed) is False

    def test_verify_password_accepts_bytes_hash(self):
        from core.security import hash_password, verify_password
        hashed_str = hash_password("Pass123!")
        hashed_bytes = hashed_str.encode("utf-8")
        assert verify_password("Pass123!", hashed_bytes) is True

    def test_verify_password_returns_false_on_invalid_hash(self):
        from core.security import verify_password
        assert verify_password("anypass", "not-a-valid-hash") is False


class TestTokenCreation:

    def test_create_access_token_contents(self):
        from core.security import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token_contents(self):
        from core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_create_reset_token_contents(self):
        from core.security import create_reset_token, decode_token
        token = create_reset_token("user-456", "user@test.com")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["email"] == "user@test.com"
        assert payload["type"] == "reset"

    def test_access_token_default_expiry(self):
        from core.security import create_access_token, decode_token
        from core.config import settings
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        expected_seconds = settings.access_token_expire_minutes * 60
        assert (expected_seconds - 120) <= delta.total_seconds() <= (expected_seconds + 120)

    def test_refresh_token_default_expiry(self):
        from core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "user-123"})
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        assert 6.9 * 24 * 3600 <= delta.total_seconds() <= 7.1 * 24 * 3600

    def test_reset_token_expiry(self):
        from core.security import create_reset_token, decode_token
        token = create_reset_token("user-123", "user@test.com")
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        assert 59 * 60 <= delta.total_seconds() <= 61 * 60


class TestTokenDecoding:

    def test_decode_valid_token(self):
        from core.security import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert isinstance(payload, dict)
        assert payload["sub"] == "user-123"

    def test_decode_expired_token(self):
        from core.security import create_access_token, decode_token
        token = create_access_token(
            {"sub": "user-123"},
            expires_delta=timedelta(seconds=-1)
        )
        result = decode_token(token)
        assert result is None

    def test_decode_malformed_token(self):
        from core.security import decode_token
        result = decode_token("not.a.token")
        assert result is None

    def test_decode_wrong_secret(self):
        import jwt
        from core.config import settings
        token = jwt.encode(
            {"sub": "user-123", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key-that-is-32-chars!x",
            algorithm=settings.algorithm,
        )
        from core.security import decode_token
        result = decode_token(token)
        assert result is None


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, sample_user):
        from core.security import create_access_token, get_current_user
        token = create_access_token({"sub": sample_user["id"]})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("core.database.execute_query", return_value=[sample_user]):
            user = await get_current_user(credentials)
        assert user["id"] == sample_user["id"]

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        from core.security import create_access_token, get_current_user
        token = create_access_token(
            {"sub": "user-123"},
            expires_delta=timedelta(seconds=-1)
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_refresh_as_access(self, sample_user):
        from core.security import create_refresh_token, get_current_user
        token = create_refresh_token({"sub": sample_user["id"]})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        from core.security import create_access_token, get_current_user
        token = create_access_token({"sub": "nonexistent-user"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("core.database.execute_query", return_value=[]):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_no_sub(self):
        from core.security import get_current_user
        import jwt
        from core.config import settings
        token = jwt.encode(
            {"type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("core.database.execute_query", return_value=[]):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)
            assert exc_info.value.status_code == 401
