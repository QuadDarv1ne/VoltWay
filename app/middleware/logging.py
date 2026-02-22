"""Middleware for request/response logging and tracking"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.metrics import http_requests_total, request_duration, errors_total

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract request info
        request_id = request.headers.get("X-Request-ID", "unknown")
        method = request.method
        path = request.url.path
        query_string = request.url.query

        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_string": query_string,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("User-Agent", "unknown"),
            },
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Track metrics
            request_duration.labels(method=method, endpoint=path).observe(duration)
            request_count.labels(
                method=method, endpoint=path, status_code=response.status_code
            ).inc()

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration * 1000,
                    "content_length": response.headers.get("Content-Length", "unknown"),
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Track error metrics
            request_count.labels(method=method, endpoint=path, status_code=500).inc()
            errors_total.labels(error_type=type(e).__name__, endpoint=path).inc()

            # Log error
            logger.error(
                "Request failed with exception",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration * 1000,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            raise


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track performance and add timing headers"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Add timing headers
        response.headers["X-Response-Time"] = str(duration)
        response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"

        # Warn if slow
        if duration > 1.0:
            logger.warning(
                "Slow request detected",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_seconds": duration,
                },
            )

        return response
