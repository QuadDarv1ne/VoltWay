import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """Configure enhanced logging for the application"""
    # Create formatters
    structured_formatter = StructuredFormatter()
    colored_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(colored_formatter)
    root_logger.addHandler(console_handler)

    # Structured file handler for production
    if not settings.debug:
        structured_handler = RotatingFileHandler(
            "voltway_structured.log", maxBytes=50 * 1024 * 1024, backupCount=10  # 50MB
        )
        structured_handler.setFormatter(structured_formatter)
        root_logger.addHandler(structured_handler)

    # Simple file handler for development
    if settings.debug:
        debug_handler = RotatingFileHandler(
            "voltway_debug.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        debug_handler.setFormatter(simple_formatter)
        root_logger.addHandler(debug_handler)

    # Error-only handler
    error_handler = RotatingFileHandler(
        "voltway_errors.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(simple_formatter)
    root_logger.addHandler(error_handler)

    # Set specific log levels for third-party libraries
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)

    # Log startup
    root_logger.info("Logging system initialized", extra={"startup": True})

    return root_logger


def log_performance(start_time: float, operation: str, **kwargs):
    """Log performance metrics"""
    duration = (datetime.now().timestamp() - start_time) * 1000  # ms
    logger = logging.getLogger("performance")
    logger.info(
        f"Operation {operation} completed",
        extra={"operation": operation, "duration_ms": round(duration, 2), **kwargs},
    )


def log_security_event(
    event_type: str, user_id: int = None, ip_address: str = None, **kwargs
):
    """Log security-related events"""
    logger = logging.getLogger("security")
    logger.info(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            **kwargs,
        },
    )


def log_cache_operation(operation: str, cache_key: str, success: bool = True, **kwargs):
    """Log cache operations"""
    logger = logging.getLogger("cache")
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        f"Cache {operation}: {cache_key}",
        extra={
            "operation": operation,
            "cache_key": cache_key,
            "success": success,
            **kwargs,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)
