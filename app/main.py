import logging
import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.exceptions import VoltWayException
from app.api.health import router as health_router
from app.api.v1 import v1_router
from app.api.v2 import v2_router
from app.core.config import settings
from app.middleware.compression import CompressionMiddleware
from app.middleware.https_redirect import HTTPSRedirectMiddleware
from app.middleware.logging import RequestLoggingMiddleware, PerformanceMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.services.notifications import notification_service
from app.utils import logging as app_logging
from app.utils.cache_cleanup import cleanup_manager
from app.utils.temp_cleanup import cleanup_on_shutdown
from app.utils.metrics import get_metrics

# Initialize Sentry for error tracking
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1 if not settings.debug else 1.0,
        environment="development" if settings.debug else "production",
    )
    logging.info("Sentry initialized")

# Setup logging
app_logging.setup_logging()
logger = logging.getLogger(__name__)

# Initialize rate limiter with settings from config
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.rate_limit_requests}/{settings.rate_limit_period_seconds}seconds"
    ],
    storage_uri="memory://",  # Use memory storage for simplicity
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "error_code": "RATE_LIMIT_EXCEEDED",
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info(f"Starting up {settings.app_name} v{settings.app_version}")
    import asyncio
    from app.services.background_tasks import background_task_manager
    from app.services.external_api import close_http_client
    from app.utils.telemetry import instrument_app, setup_opentelemetry

    # Initialize OpenTelemetry if enabled
    tracer = None
    if os.getenv("ENABLE_OTEL", "false").lower() == "true":
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        tracer = setup_opentelemetry(
            service_name=settings.app_name,
            otlp_endpoint=otlp_endpoint,
            enable_console_exporter=settings.debug,
        )
        if tracer:
            logger.info("OpenTelemetry initialized")
            instrument_app(app)

    # Start cleanup scheduler
    asyncio.create_task(cleanup_manager.start_cleanup_scheduler())

    # Start background tasks
    await background_task_manager.start()
    logger.info("Background tasks started")

    yield

    # Shutdown
    logger.info("Shutting down VoltWay application")

    # Shutdown OpenTelemetry
    if tracer:
        from app.utils.telemetry import shutdown_opentelemetry
        shutdown_opentelemetry()
        logger.info("OpenTelemetry shutdown complete")

    # Close HTTP client
    await close_http_client()
    logger.info("HTTP client closed")

    # Stop background tasks
    await background_task_manager.stop()
    logger.info("Background tasks stopped")

    # Stop cleanup scheduler
    cleanup_manager.stop_cleanup_scheduler()

    # Cleanup temporary files
    try:
        cleaned_count, error_count = cleanup_on_shutdown()
        logger.info(
            f"Temporary file cleanup: {cleaned_count} items cleaned, {error_count} errors"
        )
    except Exception as e:
        logger.error(f"Error during temporary file cleanup: {e}")


app = FastAPI(
    title=settings.app_name,
    description="Интерактивная карта зарядных станций для электромобилей",
    version=settings.app_version,
    lifespan=lifespan,
)

# Initialize app state
app.state.https_redirect = False  # Disabled by default, enable in production with HTTPS
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add SlowAPI middleware for rate limiting (disabled in testing)
if os.getenv("TESTING", "false").lower() != "true":
    app.add_middleware(SlowAPIMiddleware)
    # Enable HTTPS redirect only in production
    app.state.https_redirect = os.getenv("HTTPS_REDIRECT", "false").lower() == "true"
else:
    # Disable rate limiting in testing by setting a very high limit
    limiter._default_limits = []

# Add middleware (order matters - add in reverse order of execution)
# Compression middleware (if enabled)
if settings.enable_compression:
    app.add_middleware(
        CompressionMiddleware,
        minimum_size=settings.compression_minimum_size
    )

# HTTPS redirect only added when enabled
if app.state.https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)

# Performance and logging middleware
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Request ID for tracing
app.add_middleware(RequestIDMiddleware)

# CORS - Use settings.allowed_origins from config
allowed_origins_list = settings.allowed_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Mount Socket.IO app
app.mount("/ws", notification_service.app)

# Шаблоны
templates = Jinja2Templates(directory="app/templates")


# Exception handlers
@app.exception_handler(VoltWayException)
async def voltway_exception_handler(
    request: Request, exc: VoltWayException
) -> JSONResponse:
    """Handle custom VoltWay exceptions"""
    logger.warning(
        f"VoltWay exception: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with Sentry"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)

    # Capture in Sentry
    sentry_sdk.capture_exception(exc)

    status_code = 500
    error_code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred"

    if settings.debug:
        message = str(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "error_code": error_code,
        },
    )


# Роутеры
# Register health check router (no prefix)
app.include_router(health_router)

# Register versioned API routers
app.include_router(v1_router)
app.include_router(v2_router)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/v1/")
async def root():
    return {"message": "Welcome to VoltWay API"}


@app.get("/metrics", tags=["monitoring"], response_class=Response)
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type="text/plain")


@app.get("/api/v1/health", tags=["health"])
async def api_health():
    """API health check endpoint (deprecated, use /health)"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
