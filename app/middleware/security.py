"""
Security headers middleware for enhanced web security.

Adds security-related HTTP headers to all responses:
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security (HSTS)
- Referrer-Policy
- Permissions-Policy
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""

    def __init__(
        self,
        app,
        # Content Security Policy
        csp: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        # HSTS max age in seconds (2 years)
        hsts_max_age: int = 63072000,
        # Enable HSTS include subdomains
        hsts_include_subdomains: bool = True,
        # Enable HSTS preload
        hsts_preload: bool = False,
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            csp: Content-Security-Policy header value
            hsts_max_age: Strict-Transport-Security max-age in seconds
            hsts_include_subdomains: Include includeSubDomains in HSTS
            hsts_preload: Include preload in HSTS
        """
        super().__init__(app)
        self.csp = csp
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Add security headers to response"""
        try:
            response = await call_next(request)

            # Content Security Policy
            response.headers["Content-Security-Policy"] = self.csp

            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"

            # Clickjacking protection
            response.headers["X-Frame-Options"] = "DENY"

            # XSS protection (legacy, but still useful for older browsers)
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # HTTP Strict Transport Security (only for HTTPS)
            if request.url.scheme == "https":
                hsts_value = f"max-age={self.hsts_max_age}"
                if self.hsts_include_subdomains:
                    hsts_value += "; includeSubDomains"
                if self.hsts_preload:
                    hsts_value += "; preload"
                response.headers["Strict-Transport-Security"] = hsts_value

            # Referrer Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Permissions Policy (formerly Feature-Policy)
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(self), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )

            # Cache control for sensitive endpoints
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, proxy-revalidate"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            return response

        except Exception as e:
            logger.error(f"Error in security headers middleware: {e}")
            # Re-raise to avoid breaking the application
            raise


def create_security_headers_middleware(
    csp: str = None,
    hsts_enabled: bool = True,
    hsts_max_age: int = 63072000,
) -> SecurityHeadersMiddleware:
    """
    Factory function to create security headers middleware with custom settings.

    Args:
        csp: Custom Content-Security-Policy (optional)
        hsts_enabled: Enable HSTS header
        hsts_max_age: HSTS max-age in seconds

    Returns:
        SecurityHeadersMiddleware instance
    """
    # Default CSP for VoltWay
    default_csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com; "
        "img-src 'self' data: https: blob:; "
        "font-src 'self' data: https://unpkg.com; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "worker-src 'self' blob:;"
    )

    return SecurityHeadersMiddleware(
        app=None,  # Will be set by FastAPI
        csp=csp or default_csp,
        hsts_max_age=hsts_max_age if hsts_enabled else 0,
        hsts_include_subdomains=hsts_enabled,
        hsts_preload=hsts_enabled,
    )
