from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)

def get_sync_db():
    return SessionLocalSync()

@asynccontextmanager
async def get_db():
    """Provide a transactional asynchronous session for FastAPI endpoints"""
    async with AsyncSessionLocal() as session:
        yield session

# Synchronous engine and session for Alembic and administrative tasks
sync_database_url = settings.database_url_sync
engine = create_engine(
    sync_database_url,
    echo=settings.debug,
)
SessionLocalSync = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
