
import sys
import logging

from core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def setup_database():
    from core.db_initializer import initialize_database

    return initialize_database()


if __name__ == '__main__':
    success = setup_database()
    sys.exit(0 if success else 1)
