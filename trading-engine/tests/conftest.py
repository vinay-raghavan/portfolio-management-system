"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from engine.config import settings
from engine.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def internal_headers():
    """Headers with valid internal API key."""
    return {"X-Internal-Key": settings.INTERNAL_API_KEY}
