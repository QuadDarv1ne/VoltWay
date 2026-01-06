import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logging():
    """Configure logging for the application"""
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if settings.debug:
        file_handler = RotatingFileHandler(
            "voltway.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for third-party libraries
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)
