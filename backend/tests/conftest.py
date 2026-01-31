"""Pytest configuration and fixtures for backend tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
