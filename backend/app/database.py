"""
SQLAlchemy async database configuration.
Provides AsyncEngine and AsyncSession factory for the entire application.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from typing import AsyncGenerator
from app.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Async Engine Factory
# ─────────────────────────────────────────────────────────────────────────────
def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine.
    - Uses AsyncPG driver (postgres+asyncpg://)
    - Pools connections in production, disables in testing
    - Echo SQL in debug mode
    """
    # Use QueuePool in production, NullPool in testing
    pool_class = NullPool if settings.debug else QueuePool

    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_class=pool_class,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            "timeout": 10,
            "server_settings": {
                "application_name": "devpulse",
            },
        },
    )
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# Global Engine Instance
# ─────────────────────────────────────────────────────────────────────────────
engine: AsyncEngine = create_engine()


# ─────────────────────────────────────────────────────────────────────────────
# AsyncSession Factory
# ─────────────────────────────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Session Dependency for FastAPI
# ─────────────────────────────────────────────────────────────────────────────
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.
    Usage in endpoints:
        async def my_endpoint(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
