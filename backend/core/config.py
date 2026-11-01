from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from dotenv import load_dotenv
import os
import logging
import secrets
import json
import ipaddress
import sys
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32":
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass

env_file = Path(__file__).resolve().parents[2] / ".env"
if env_file.exists():
    load_dotenv(env_file, encoding='utf-8-sig')

logger = logging.getLogger(__name__)

DEFAULT_CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
DEFAULT_TRUSTED_PROXIES = ['127.0.0.1', '::1']


def parse_cors_origins(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None or value == '':
        raw_origins = DEFAULT_CORS_ORIGINS
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raw_origins = DEFAULT_CORS_ORIGINS
        elif stripped.startswith('['):
            try:
                raw_origins = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError('CORS_ORIGINS must be a CSV list or a JSON array') from exc
        else:
            raw_origins = stripped.split(',')
    elif isinstance(value, (list, tuple)):
        raw_origins = list(value)
    else:
        raise ValueError('CORS_ORIGINS must be a CSV list or a JSON array')

    if not isinstance(raw_origins, list):
        raise ValueError('CORS_ORIGINS JSON value must be an array')

    normalized_origins: list[str] = []
    seen: set[str] = set()
    for raw_origin in raw_origins:
        if not isinstance(raw_origin, str):
            raise ValueError('CORS_ORIGINS entries must be strings')

        origin = raw_origin.strip().strip('"').strip("'")
        if not origin:
            continue
        if origin in {'*', 'null'}:
            raise ValueError('CORS_ORIGINS cannot contain wildcard or null origins when credentials are enabled')

        parsed = urlparse(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValueError(f'Invalid CORS origin: {origin}')
        if parsed.username or parsed.password:
            raise ValueError(f'CORS origin cannot contain credentials: {origin}')
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError(f'Invalid CORS origin port: {origin}') from exc
        if parsed.path not in {'', '/'} or parsed.params or parsed.query or parsed.fragment:
            raise ValueError(f'CORS origin must not include path, query or fragment: {origin}')

        normalized = f'{parsed.scheme}://{parsed.netloc.lower()}'
        if normalized not in seen:
            normalized_origins.append(normalized)
            seen.add(normalized)

    if not normalized_origins:
        raise ValueError('CORS_ORIGINS must contain at least one valid origin')
    return normalized_origins


def _cors_origins() -> list[str]:
    return parse_cors_origins(os.getenv('CORS_ORIGINS'))


def parse_trusted_proxies(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None or value == '':
        raw_proxies = DEFAULT_TRUSTED_PROXIES
    elif isinstance(value, str):
        raw_proxies = value.split(',')
    elif isinstance(value, (list, tuple)):
        raw_proxies = list(value)
    else:
        raise ValueError('TRUSTED_PROXIES must be a CSV list of IP addresses or CIDR ranges')

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_proxy in raw_proxies:
        if not isinstance(raw_proxy, str):
            raise ValueError('TRUSTED_PROXIES entries must be strings')
        proxy = raw_proxy.strip()
        if not proxy:
            continue
        try:
            network = ipaddress.ip_network(proxy, strict=False)
        except ValueError as exc:
            raise ValueError(f'Invalid trusted proxy: {proxy}') from exc
        network_value = str(network)
        if network_value not in seen:
            normalized.append(network_value)
            seen.add(network_value)

    if not normalized:
        raise ValueError('TRUSTED_PROXIES must contain at least one valid IP address or CIDR range')
    return normalized


def _trusted_proxies() -> list[str]:
    return parse_trusted_proxies(os.getenv('TRUSTED_PROXIES'))


class Settings(BaseSettings):

    database_url: str = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/contratia_db')
    secret_key: str = os.getenv('SECRET_KEY', '')
    algorithm: str = os.getenv('ALGORITHM', 'HS256')
    access_token_expire_minutes: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    refresh_token_expire_days: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))
    debug: bool = os.getenv('DEBUG', os.getenv('APP_DEBUG', 'False')).lower() == 'true'
    
    cors_origins: list[str] = Field(
        default_factory=_cors_origins,
        validation_alias='CONTRATIA_INTERNAL_CORS_ORIGINS',
    )
    trusted_proxies: list[str] = Field(
        default_factory=_trusted_proxies,
        validation_alias='CONTRATIA_INTERNAL_TRUSTED_PROXIES',
    )

    smtp_host: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    smtp_from: str = os.getenv('SMTP_FROM', '')
    smtp_from_name: str = os.getenv('SMTP_FROM_NAME', 'ContratIA')
    frontend_url: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    google_client_id: str = os.getenv('GOOGLE_CLIENT_ID', '')
    
    redis_url: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-5.4-mini')
    openai_fallback_model: str = os.getenv('OPENAI_FALLBACK_MODEL', 'gpt-4.1-mini')
    openai_embedding_model: str = os.getenv(
        'OPENAI_EMBEDDING_MODEL',
        'text-embedding-3-small',
    )
    
    qdrant_url: str = os.getenv('QDRANT_URL', 'http://localhost:6333')
    qdrant_api_key: str = os.getenv('QDRANT_API_KEY', '')
    qdrant_collection: str = os.getenv('QDRANT_COLLECTION', '')
    rag_score_threshold: float = float(os.getenv('RAG_SCORE_THRESHOLD', '0.35'))
    chat_max_input_chars: int = int(os.getenv('CHAT_MAX_INPUT_CHARS', '4000'))
    chat_max_history_tokens: int = int(os.getenv('CHAT_MAX_HISTORY_TOKENS', '6000'))
    chat_max_contract_tokens: int = int(os.getenv('CHAT_MAX_CONTRACT_TOKENS', '10000'))
    chat_max_output_tokens: int = int(os.getenv('CHAT_MAX_OUTPUT_TOKENS', '1200'))
    chat_openai_timeout_seconds: float = float(os.getenv('CHAT_OPENAI_TIMEOUT_SECONDS', '45'))

    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {'true', '1', 'yes', 'on', 'debug'}:
                return True
            if normalized in {'false', '0', 'no', 'off', 'release', 'production', 'prod', ''}:
                return False
        return value

    @field_validator(
        'openai_model',
        'openai_fallback_model',
        'openai_embedding_model',
    )
    @classmethod
    def validate_openai_model(cls, value: str) -> str:
        model = value.strip()
        if not model:
            raise ValueError('OpenAI model names cannot be empty')
        return model

    @field_validator('cors_origins', mode='before')
    @classmethod
    def validate_cors_origins(cls, value):
        return parse_cors_origins(value)

    @field_validator('trusted_proxies', mode='before')
    @classmethod
    def validate_trusted_proxies(cls, value):
        return parse_trusted_proxies(value)

    model_config = ConfigDict(case_sensitive=False, populate_by_name=True)


settings = Settings()

if not settings.secret_key:
    settings.secret_key = secrets.token_urlsafe(64)
    logger.warning("SECRET_KEY no configurada. Se usa clave auto-generada. Las sesiones no persistirán entre reinicios.")
    logger.warning("Establece SECRET_KEY en .env para uso en producción.")

if settings.debug:
    db_url = settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url
    logger.info("Configuración cargada (modo DEBUG)")
    logger.debug("Database: %s", db_url)
