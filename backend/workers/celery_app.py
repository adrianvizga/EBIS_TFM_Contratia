
from celery import Celery
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.logging_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

env_path = BASE_DIR.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, encoding='utf-8', override=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger.info(f"Celery connecting to Redis at: {REDIS_URL}")

celery_app = Celery(
    "workers",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(['workers'])

if __name__ == '__main__':
    celery_app.start()
