
import os
import time
import uuid
import logging
import warnings

warnings.filterwarnings("ignore", message="Api key is used with an insecure connection", category=UserWarning)

from core.logging_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.endpoints import auth, contracts, notifications, settings as settings_endpoint, agent, generated_contracts, usage

app = FastAPI(
    title="ContratIA API",
    description="API for intelligent contract management",
    version="1.0.0",
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger.info("BACKEND STARTED -- PID: %d | debug=%s", os.getpid(), settings.debug)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    client = request.client.host if request.client else "unknown"
    logger.info(
        "[%s] --> %s %s (client=%s)",
        request_id, request.method, request.url.path, client,
    )

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception(
            "[%s] ERR %s %s -- error no controlado (%.1f ms)",
            request_id, request.method, request.url.path, elapsed,
        )
        raise

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        "[%s] <-- %s %s -- %d (%.1f ms)",
        request_id, request.method, request.url.path,
        response.status_code, elapsed,
    )
    response.headers["X-Request-ID"] = request_id
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Evita que las respuestas JSON y HTML pierdan caracteres Unicode.
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type or "text/html" in content_type:
        if "charset" not in content_type:
            response.headers["content-type"] = f"{content_type}; charset=utf-8"
    
    return response



from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(notifications.router)
app.include_router(settings_endpoint.router)
app.include_router(agent.router)
app.include_router(generated_contracts.router)
app.include_router(usage.router)


@app.on_event("startup")
async def mark_stale_processing_contracts():
    """Mark contracts stuck in 'processing' as 'error' on startup.

    If the server (or Celery worker) crashed mid-analysis the task is lost but
    the DB row stays in 'processing' forever.  On restart we reset those rows
    so the user can trigger a manual retry via the existing retry endpoint.
    """
    try:
        from core.database import execute_transaction
        execute_transaction([
            (
                """
                UPDATE contracts
                SET status = 'error',
                    error_message = 'El análisis fue interrumpido por un reinicio del servidor. Por favor, vuelva a intentarlo.',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'processing'
                """,
                {},
            ),
            (
                """
                UPDATE contract_analyses
                SET status = 'error',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'processing'
                """,
                {},
            ),
        ])
        logger.info("Startup cleanup: contratos bloqueados en 'processing' marcados como 'error'")
    except Exception:
        logger.exception("Startup cleanup falló — los contratos bloqueados permanecerán en 'processing'")


@app.get("/")
async def root():
    return {
        "message": "ContratIA API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get('/ready')
def readiness_check():
    checks = {}
    try:
        from core.database import execute_query

        execute_query('SELECT 1 AS ready')
        checks['postgres'] = 'healthy'
    except Exception as error:
        logger.error('Readiness PostgreSQL falló: %s', error)
        checks['postgres'] = 'unhealthy'

    try:
        import redis

        redis.from_url(settings.redis_url, socket_connect_timeout=3).ping()
        checks['redis'] = 'healthy'
    except Exception as error:
        logger.error('Readiness Redis falló: %s', error)
        checks['redis'] = 'unhealthy'

    try:
        from qdrant_client import QdrantClient

        QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=3,
        ).get_collections()
        checks['qdrant'] = 'healthy'
    except Exception as error:
        logger.error('Readiness Qdrant falló: %s', error)
        checks['qdrant'] = 'unhealthy'

    ready = all(value == 'healthy' for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={'status': 'ready' if ready else 'not_ready', 'checks': checks},
    )
