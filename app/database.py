from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base

# Asynchronous engine (primary)
# Convert database URL to async version
async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
if "postgresql" in settings.database_url:
    async_database_url = settings.database_url.replace(
        "postgresql", "postgresql+asyncpg"
    )

# Configure engine based on database type
engine_kwargs = {
    "echo": settings.debug,
    "future": True,
}

# Add pool settings only for PostgreSQL
if "postgresql" in async_database_url:
    engine_kwargs.update({
        "pool_size": 20,  # Connection pool size
        "max_overflow": 10,  # Max overflow connections
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    })

async_engine = create_async_engine(async_database_url, **engine_kwargs)

# Synchronous engine (for migrations only)
sync_engine_kwargs = {}
if "postgresql" in settings.database_url:
    sync_engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_engine(settings.database_url, **sync_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db():
    """Synchronous database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Asynchronous database session generator"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
