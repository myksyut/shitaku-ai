"""Tests for API dependencies module."""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from src.presentation.api.v1.dependencies import get_current_user_id


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self) -> None:
        """有効なトークンでユーザーIDが取得できること"""
        # Arrange
        expected_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_credentials = AsyncMock()
        mock_credentials.credentials = "valid_token"

        with patch("src.presentation.api.v1.dependencies.verify_supabase_jwt") as mock_verify:
            mock_verify.return_value = {"sub": expected_user_id}

            # Act
            result = await get_current_user_id(mock_credentials)

            # Assert
            assert result == UUID(expected_user_id)
            mock_verify.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self) -> None:
        """無効なトークンで401エラーが返却されること"""
        # Arrange
        mock_credentials = AsyncMock()
        mock_credentials.credentials = "invalid_token"

        with patch("src.presentation.api.v1.dependencies.verify_supabase_jwt") as mock_verify:
            mock_verify.return_value = None

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(mock_credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid or expired token"
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_token_without_sub_returns_401(self) -> None:
        """subフィールドがないトークンで401エラーが返却されること"""
        # Arrange
        mock_credentials = AsyncMock()
        mock_credentials.credentials = "token_without_sub"

        with patch("src.presentation.api.v1.dependencies.verify_supabase_jwt") as mock_verify:
            mock_verify.return_value = {"email": "test@example.com"}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(mock_credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "User ID not found in token"
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_invalid_uuid_format_returns_401(self) -> None:
        """不正なUUID形式で401エラーが返却されること"""
        # Arrange
        mock_credentials = AsyncMock()
        mock_credentials.credentials = "token_with_invalid_uuid"

        with patch("src.presentation.api.v1.dependencies.verify_supabase_jwt") as mock_verify:
            mock_verify.return_value = {"sub": "not-a-valid-uuid"}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(mock_credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid user ID format"
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
