from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import auth, favorites, notifications, stations
from app.core.config import settings
from app.services.notifications import notification_service
from app.utils import logging

# Setup logging
logging.setup_logging()

# Note: Database tables should be created via Alembic migrations
# Base.metadata.create_all(bind=engine)  # Removed for production best practices

# Note: Sample data should be added via scripts or migrations
# add_sample_data()  # Removed for production best practices

app = FastAPI(
    title="VoltWay",
    description="Интерактивная карта зарядных станций для электромобилей",
    version="1.0.0",
)

# Initialize notification service later in lifecycle
# notification_service.initialize_sockets(app)
# CORS - Allow localhost for development; configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],  # Add your frontend URLs
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

# Роутеры
app.include_router(stations.router, prefix="/api/v1", tags=["stations"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(favorites.router, prefix="/api/v1", tags=["favorites"])
app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])

# Note: Database tables should be created via Alembic migrations
# Base.metadata.create_all(bind=engine)  # Removed for production best practices


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
