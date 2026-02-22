"""
Response compression middleware.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware


class CompressionMiddleware(GZipMiddleware):
    """
    Compress responses using gzip.
    
    Inherits from Starlette's GZipMiddleware with sensible defaults.
    """

    def __init__(self, app, minimum_size: int = 500):
        """
        Initialize compression middleware.
        
        Args:
            app: ASGI application
            minimum_size: Minimum response size in bytes to compress (default: 500)
        """
        super().__init__(app, minimum_size=minimum_size)
