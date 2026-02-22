"""
HTTPS Redirect Middleware.

Redirects HTTP requests to HTTPS in production environment.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP to HTTPS.

    Only active when HTTPS_REDIRECT=true environment variable is set.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if HTTPS redirect is enabled
        if not request.app.state.https_redirect:
            return await call_next(request)

        # Skip redirect for localhost in development
        if request.client and request.client.host in ["127.0.0.1", "localhost"]:
            return await call_next(request)

        # Check if already using HTTPS
        if request.headers.get("x-forwarded-proto") == "https":
            return await call_next(request)

        # Redirect to HTTPS
        url = request.url
        if url.scheme == "http":
            https_url = url.replace(scheme="https")
            logger.debug(f"Redirecting to HTTPS: {https_url}")
            return RedirectResponse(https_url, status_code=301)

        return await call_next(request)
