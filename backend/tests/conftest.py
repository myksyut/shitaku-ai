"""Pytest configuration and fixtures for backend tests."""

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.presentation.api.v1.dependencies import get_current_user_id

# テスト用固定ユーザーID
TEST_USER_ID = uuid4()


def _mock_current_user_id() -> UUID:
    """テスト用ユーザーIDを返すモック関数."""
    return TEST_USER_ID


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client() -> Generator[TestClient, None, None]:
    """Create a test client with mocked authentication.

    認証済みユーザーをシミュレートするため、
    get_current_user_id依存関係をオーバーライドする。
    """
    app.dependency_overrides[get_current_user_id] = _mock_current_user_id
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_id() -> UUID:
    """テスト用ユーザーID."""
    return TEST_USER_ID
