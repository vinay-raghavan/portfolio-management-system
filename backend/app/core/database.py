"""Database configuration and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
# Note: pool_pre_ping=False to avoid MissingGreenlet errors after long operations
# The pool_recycle handles stale connections instead
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=False,  # Disabled - causes greenlet errors after long operations
    pool_size=5,
    max_overflow=10,
    pool_recycle=180,  # Recycle connections every 3 minutes
    pool_timeout=30,  # Wait max 30s for a connection from pool
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


async def init_db() -> None:
    """Initialize database - verify connection.

    Note: Tables are managed by Alembic migrations.
    Run: alembic upgrade head
    """
    async with engine.begin() as conn:
        # Just verify connection - Alembic manages schema
        await conn.execute(text("SELECT 1"))


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
