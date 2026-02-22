"""Prometheus metrics for monitoring"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
)
import time
from typing import Callable
from functools import wraps

# Create metrics registry
registry = CollectorRegistry()

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Database metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    registry=registry,
)

db_connection_pool = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    registry=registry,
)

# Cache metrics
cache_hits = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_name"],
    registry=registry,
)

cache_misses = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_name"],
    registry=registry,
)

cache_size = Gauge(
    "cache_size_bytes",
    "Cache size in bytes",
    ["cache_name"],
    registry=registry,
)

# Application metrics
active_connections = Gauge(
    "active_connections",
    "Active WebSocket connections",
    registry=registry,
)

background_tasks = Gauge(
    "background_tasks_active",
    "Active background tasks",
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "endpoint"],
    registry=registry,
)


def track_request(endpoint: str):
    """Decorator to track request metrics"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                request_duration.labels(method="GET", endpoint=endpoint).observe(
                    duration
                )
                request_count.labels(
                    method="GET", endpoint=endpoint, status_code=200
                ).inc()
                return result
            except Exception as e:
                duration = time.time() - start_time
                request_duration.labels(method="GET", endpoint=endpoint).observe(
                    duration
                )
                request_count.labels(
                    method="GET", endpoint=endpoint, status_code=500
                ).inc()
                errors_total.labels(
                    error_type=type(e).__name__, endpoint=endpoint
                ).inc()
                raise

        return wrapper

    return decorator


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest(registry)
