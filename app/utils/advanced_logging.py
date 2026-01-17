"""Advanced logging configuration with JSON structured logging"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, default=str)


class LoggerWithExtra(logging.Logger):
    """Logger that supports extra fields"""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=None):
        if extra is None:
            extra = {}
        # Store extra info for JSON formatter
        self.extra_data = extra
        super()._log(level, msg, args, exc_info, extra, stack_info)


def setup_logging() -> None:
    """Setup advanced logging configuration"""

    # Use custom logger class
    logging.setLoggerClass(LoggerWithExtra)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    console_formatter = JSONFormatter()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_dir / "voltway.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(console_formatter)
    logger.addHandler(file_handler)

    # Error file handler
    error_handler = RotatingFileHandler(
        log_dir / "voltway_errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(console_formatter)
    logger.addHandler(error_handler)

    # Disable noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger.info("Logging configured", extra={"environment": "production" if not settings.debug else "development"})


def get_logger(name: str) -> logging.Logger:
    """Get logger with extra support"""
    return logging.getLogger(name)
