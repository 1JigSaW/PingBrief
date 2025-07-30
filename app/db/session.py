# app/db/session.py

from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings

settings = get_settings()

# ─── Асинхронный движок для FastAPI ────────────────────────────────
async_engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

@asynccontextmanager
async def get_db():
    """Асинхронная сессия для FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session

# ─── Синхронный движок для Celery ─────────────────────────────────
# убираем +asyncpg, чтобы SQLAlchemy понимал, что это sync-DSN
sync_database_url = settings.database_url.replace("+asyncpg", "")
sync_engine = create_engine(sync_database_url, echo=settings.debug)
SessionLocalSync = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)
