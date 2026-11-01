import pytest
from unittest.mock import patch
import os

pytestmark = pytest.mark.unit


class TestConfigDefaults:

    def test_default_database_url(self):
        from core.config import Settings
        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
            assert "postgresql://" in s.database_url
            assert "localhost" in s.database_url or "5432" in s.database_url

    def test_env_override_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://u:p@myhost:5433/mydb"}):
            from core.config import Settings
            s = Settings()
            assert s.database_url == "postgresql://u:p@myhost:5433/mydb"

    def test_openai_model_can_be_configured(self):
        from core.config import Settings

        s = Settings(openai_model="custom-contract-model")

        assert s.openai_model == "custom-contract-model"

    def test_openai_model_rejects_empty_value(self):
        from pydantic import ValidationError
        from core.config import Settings

        with pytest.raises(ValidationError, match="OpenAI model"):
            Settings(openai_model="   ")

    def test_openai_fallback_model_can_be_configured(self):
        from core.config import Settings

        s = Settings(openai_fallback_model="custom-fallback-model")

        assert s.openai_fallback_model == "custom-fallback-model"

    def test_openai_embedding_model_can_be_configured(self):
        from core.config import Settings

        s = Settings(openai_embedding_model="custom-embedding-model")

        assert s.openai_embedding_model == "custom-embedding-model"

    def test_auto_secret_key(self):
        from core.config import settings
        assert settings.secret_key
        assert len(settings.secret_key) > 10

    def test_default_debug_false(self):
        clean_env = {k: v for k, v in os.environ.items() if k != "DEBUG"}
        clean_env["DEBUG"] = "False"
        with patch.dict(os.environ, clean_env, clear=True):
            from core.config import Settings
            s = Settings()
            assert s.debug is False

    def test_release_debug_value_is_false(self):
        with patch.dict(os.environ, {"DEBUG": "release"}):
            from core.config import Settings
            s = Settings()
            assert s.debug is False

    def test_cors_origins_list(self):
        from core.config import settings
        assert isinstance(settings.cors_origins, list)
        assert all(isinstance(o, str) for o in settings.cors_origins)
        assert len(settings.cors_origins) > 0

    def test_cors_origins_csv_env(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000/, http://localhost:5173"}):
            from core.config import Settings
            s = Settings()
            assert s.cors_origins == ["http://localhost:3000", "http://localhost:5173"]

    def test_cors_origins_json_env_compatibility(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": '["https://app.example.com","http://localhost:5173"]'}):
            from core.config import Settings
            s = Settings()
            assert s.cors_origins == ["https://app.example.com", "http://localhost:5173"]

    def test_cors_origins_rejects_wildcard_with_credentials(self):
        from core.config import parse_cors_origins
        with pytest.raises(ValueError):
            parse_cors_origins("*")

    def test_cors_origins_rejects_paths(self):
        from core.config import parse_cors_origins
        with pytest.raises(ValueError):
            parse_cors_origins("https://app.example.com/private")

    def test_trusted_proxies_csv_env(self):
        with patch.dict(os.environ, {"TRUSTED_PROXIES": "127.0.0.1, 172.16.0.0/12"}):
            from core.config import Settings
            s = Settings()
            assert s.trusted_proxies == ["127.0.0.1/32", "172.16.0.0/12"]

    def test_trusted_proxies_rejects_invalid_value(self):
        from core.config import parse_trusted_proxies
        with pytest.raises(ValueError):
            parse_trusted_proxies("not-an-ip")

    def test_default_access_token_expire(self):
        from core.config import settings
        assert isinstance(settings.access_token_expire_minutes, int)
        assert settings.access_token_expire_minutes > 0

    def test_default_refresh_token_expire(self):
        from core.config import settings
        assert settings.refresh_token_expire_days == 7

    def test_algorithm_default(self):
        from core.config import settings
        assert settings.algorithm == "HS256"
