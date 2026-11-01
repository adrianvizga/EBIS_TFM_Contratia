
import os
import re
import hashlib
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if not root.handlers:
        # Solo si no se ha inicializado aún el logging centralizado
        from core.logging_config import setup_logging as central_setup
        central_setup()

    # Silenciar loggers ruidosos de terceros
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logger.debug("RAG logging configurado (level=%s)", logging.getLevelName(level))

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    dotenv_path = os.path.join(backend_dir, '..', '.env')
    
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        logger.debug('No .env file found at %s; using process environment', dotenv_path)

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def get_safe_hash(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
