"""Test fixtures and configuration."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock

from app.core.database import Base, get_db
from app.main import app

# Use SQLite in-memory database for tests (no external dependencies)
# This avoids needing a running PostgreSQL server for unit/integration tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_engine():
    """Create and properly dispose test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    # Properly dispose engine to clean up threads
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Create test database session with in-memory SQLite."""
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    """Create test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Mock fixtures for external services
@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for external API calls."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.aclose = AsyncMock()
    return mock

