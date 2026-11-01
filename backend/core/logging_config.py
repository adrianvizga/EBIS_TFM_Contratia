
import os
import sys
import logging
import json
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


_BACKEND_DIR = Path(__file__).resolve().parent.parent


class JSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry, ensure_ascii=False)


_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_TEXT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level(level_str: str) -> int:
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return mapping.get(level_str.upper(), logging.INFO)


def setup_logging() -> None:
    level_str = os.getenv("LOG_LEVEL", "INFO")
    output = os.getenv("LOG_OUTPUT", "console").lower()
    log_file = os.getenv("LOG_FILE", str(_BACKEND_DIR / "logs" / "contratia.log"))
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    log_format = os.getenv("LOG_FORMAT", "text").lower()

    level = _resolve_level(level_str)

    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(_TEXT_FORMAT, datefmt=_TEXT_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Evita duplicados cuando se configura más de una vez, como en los tests.
    root_logger.handlers.clear()

    if output in ("console", "both"):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if output in ("file", "both"):
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce el ruido de librerías externas.
    for noisy in (
        "httpx", "openai", "httpcore", "qdrant_client",
        "urllib3", "asyncio", "multipart",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Uvicorn registra sus accesos internos a partir de WARNING.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger.info(
        "Logging configurado -- nivel=%s destino=%s formato=%s",
        level_str.upper(), output, log_format,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
