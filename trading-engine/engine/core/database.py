"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from engine.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Create async engine
# connect_args notes (asyncpg):
# - command_timeout bounds any single query so a dead socket surfaces fast
# - server_settings enables TCP keepalives on the server side so long-idle
#   sessions (e.g. while fetching quotes) don't get silently dropped by
#   firewalls / container networks
# - statement_timeout is a safety net against runaway queries
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,  # Recycle connections every 5 min to avoid stale conns during long scheduled runs
    pool_timeout=60,  # Wait max 60s for a connection from pool
    connect_args={
        "command_timeout": 60,
        "server_settings": {
            "application_name": "trading-engine",
            "tcp_keepalives_idle": "60",
            "tcp_keepalives_interval": "10",
            "tcp_keepalives_count": "3",
            "statement_timeout": "60000",
        },
    },
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
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession]:
    """Context manager for database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
