"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from engine.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession]:
    """Context manager for database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False
