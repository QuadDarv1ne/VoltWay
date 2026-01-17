import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import auth, favorites, monitoring, notifications, stations
from app.api.exceptions import VoltWayException
from app.core.config import settings
from app.services.notifications import notification_service
from app.utils import logging as app_logging
from app.utils.cache_cleanup import cleanup_manager
from app.utils.temp_cleanup import cleanup_on_shutdown

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

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting up VoltWay application")
    import asyncio
    asyncio.create_task(cleanup_manager.start_cleanup_scheduler())
    yield
    # Shutdown
    logger.info("Shutting down VoltWay application")
    cleanup_manager.stop_cleanup_scheduler()
    try:
        cleaned_count, error_count = cleanup_on_shutdown()
        logger.info(f"Temporary file cleanup: {cleaned_count} items cleaned, {error_count} errors")
    except Exception as e:
        logger.error(f"Error during temporary file cleanup: {e}")


app = FastAPI(
    title="VoltWay",
    description="Интерактивная карта зарядных станций для электромобилей",
    version="1.0.0",
    lifespan=lifespan,
)

# Apply rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Allow localhost for development; configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ] if settings.debug else ["https://example.com"],  # Configure for production
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
def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "error_code": "RATE_LIMIT_EXCEEDED",
        },
    )


@app.exception_handler(VoltWayException)
async def voltway_exception_handler(request: Request, exc: VoltWayException) -> JSONResponse:
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
app.include_router(stations.router, prefix="/api/v1", tags=["stations"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(favorites.router, prefix="/api/v1", tags=["favorites"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])
# app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])  # Temporarily disabled


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/v1/")
async def root():
    return {"message": "Welcome to VoltWay API"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2026-01-06T00:00:00Z",
    }  # Use datetime.utcnow() in real implementation


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
