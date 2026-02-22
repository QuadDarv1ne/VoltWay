"""
Prometheus metrics for monitoring and alerting.

Provides:
- System metrics (CPU, memory)
- Application metrics (requests, errors)
- Business metrics (stations, searches)
- Database metrics (queries, connections)
- Cache metrics
- External API metrics
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
)
import time
import psutil
from typing import Callable, Optional
from functools import wraps
from contextlib import contextmanager

# Use default registry for better integration
# registry = REGISTRY

# =============================================================================
# System Metrics
# =============================================================================

cpu_usage = Gauge(
    "voltway_cpu_usage_percent",
    "Current CPU usage percentage",
)

memory_usage = Gauge(
    "voltway_memory_usage_bytes",
    "Current memory usage in bytes",
    ["type"],
)

# =============================================================================
# Application Metrics
# =============================================================================

http_requests_total = Counter(
    "voltway_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

request_duration = Histogram(
    "voltway_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

requests_in_progress = Gauge(
    "voltway_requests_in_progress",
    "Number of requests currently being processed",
    ["endpoint"],
)

# =============================================================================
# Business Metrics
# =============================================================================

total_stations = Gauge(
    "voltway_stations_total",
    "Total number of stations in database",
)

stations_by_status = Gauge(
    "voltway_stations_by_status",
    "Number of stations by status",
    ["status"],
)

station_searches_total = Counter(
    "voltway_station_searches_total",
    "Total station searches",
    ["search_type", "has_location", "has_filters"],
)

geospatial_queries_total = Counter(
    "voltway_geospatial_queries_total",
    "Total geospatial queries",
    ["result"],
)

connector_types_total = Gauge(
    "voltway_connector_types_total",
    "Number of stations by connector type",
    ["connector_type"],
)

avg_power_by_connector = Gauge(
    "voltway_avg_power_kw_by_connector",
    "Average power in kW by connector type",
    ["connector_type"],
)

# =============================================================================
# Database Metrics
# =============================================================================

db_query_duration = Histogram(
    "voltway_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

db_connection_pool = Gauge(
    "voltway_db_connection_pool_size",
    "Database connection pool size",
    ["state"],
)

# =============================================================================
# Cache Metrics
# =============================================================================

cache_hits = Counter(
    "voltway_cache_hits_total",
    "Total cache hits",
    ["cache_name"],
)

cache_misses = Counter(
    "voltway_cache_misses_total",
    "Total cache misses",
    ["cache_name"],
)

cache_size = Gauge(
    "voltway_cache_size_bytes",
    "Cache size in bytes",
    ["cache_name"],
)

cache_hit_ratio = Gauge(
    "voltway_cache_hit_ratio",
    "Cache hit ratio (0-1)",
)

# =============================================================================
# External API Metrics
# =============================================================================

external_api_calls_total = Counter(
    "voltway_external_api_calls_total",
    "Total external API calls",
    ["api", "status"],
)

external_api_duration = Histogram(
    "voltway_external_api_duration_seconds",
    "External API response time in seconds",
    ["api"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

circuit_breaker_state = Gauge(
    "voltway_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["api"],
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

active_connections = Gauge(
    "voltway_active_websocket_connections",
    "Active WebSocket connections",
)

notifications_sent_total = Counter(
    "voltway_notifications_sent_total",
    "Total notifications sent",
    ["type"],
)

# =============================================================================
# Error Metrics
# =============================================================================

errors_total = Counter(
    "voltway_errors_total",
    "Total errors",
    ["error_type", "endpoint"],
)

# =============================================================================
# Background Tasks Metrics
# =============================================================================

background_tasks_active = Gauge(
    "voltway_background_tasks_active",
    "Active background tasks",
)

background_tasks_total = Counter(
    "voltway_background_tasks_total",
    "Total background tasks executed",
    ["task_name", "status"],
)

# =============================================================================
# Helper Functions
# =============================================================================


def update_system_metrics():
    """Update system metrics"""
    cpu_usage.set(psutil.cpu_percent(interval=0.1))

    mem = psutil.virtual_memory()
    memory_usage.labels(type="total").set(mem.total)
    memory_usage.labels(type="used").set(mem.used)
    memory_usage.labels(type="available").set(mem.available)
    memory_usage.labels(type="percent").set(mem.percent)


def update_station_metrics(
    total: int,
    by_status: dict,
    by_connector: dict,
    avg_power: dict,
):
    """
    Update station-related business metrics.

    Args:
        total: Total number of stations
        by_status: Dict of status -> count
        by_connector: Dict of connector_type -> count
        avg_power: Dict of connector_type -> avg power
    """
    total_stations.set(total)

    for status, count in by_status.items():
        stations_by_status.labels(status=status).set(count)

    for connector, count in by_connector.items():
        connector_types_total.labels(connector_type=connector).set(count)

    for connector, power in avg_power.items():
        avg_power_by_connector.labels(connector_type=connector).set(power)


def update_cache_metrics(
    hits: int,
    misses: int,
    size: int,
    cache_name: str = "default",
):
    """
    Update cache metrics.

    Args:
        hits: Total cache hits
        misses: Total cache misses
        size: Current cache size in bytes
        cache_name: Name of the cache
    """
    cache_hits.labels(cache_name=cache_name).inc(hits)
    cache_misses.labels(cache_name=cache_name).inc(misses)
    cache_size.labels(cache_name=cache_name).set(size)

    total = hits + misses
    if total > 0:
        cache_hit_ratio.set(hits / total)


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    update_system_metrics()
    return generate_latest(REGISTRY)


def get_metrics_response():
    """Get Prometheus metrics as Starlette response"""
    from starlette.responses import Response

    return Response(
        content=get_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )


# =============================================================================
# Context Managers and Decorators
# =============================================================================


@contextmanager
def track_request_duration(endpoint: str, method: str = "GET"):
    """Context manager to track request duration"""
    requests_in_progress.labels(endpoint=endpoint).inc()
    start_time = time.time()
    status_code = 500
    try:
        yield
        status_code = 200
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        requests_in_progress.labels(endpoint=endpoint).dec()
        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()


@contextmanager
def track_db_query(operation: str, table: str = "unknown"):
    """Context manager to track database query duration"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        db_query_duration.labels(operation=operation, table=table).observe(duration)


@contextmanager
def track_external_api(api: str):
    """Context manager to track external API calls"""
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        external_api_calls_total.labels(api=api, status=status).inc()
        external_api_duration.labels(api=api).observe(duration)


def track_background_task(task_name: str):
    """Decorator to track background task execution"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            background_tasks_active.inc()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                background_tasks_active.dec()
                background_tasks_total.labels(
                    task_name=task_name, status=status
                ).inc()

        return wrapper

    return decorator
