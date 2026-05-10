"""Pytest configuration and shared fixtures."""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def async_client():
    """Yield an async HTTP client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
