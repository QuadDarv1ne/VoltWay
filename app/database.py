from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base

# Synchronous engine (for backward compatibility)
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous engine
# Convert database URL to async version
async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
if "postgresql" in settings.database_url:
    async_database_url = settings.database_url.replace("postgresql", "postgresql+asyncpg")

async_engine = create_async_engine(
    async_database_url,
    echo=settings.debug,
    future=True,
)

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
