"""GoogleAuthUseCases tests.

Tests for Google OAuth use cases following AAA pattern.
All external dependencies (GoogleOAuthClient, Repository, encryption) are mocked.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.use_cases import google_auth_use_cases
from src.application.use_cases.google_auth_use_cases import (
    DeleteGoogleIntegrationUseCase,
    GetGoogleIntegrationsUseCase,
    HandleGoogleCallbackUseCase,
    RefreshGoogleTokenUseCase,
    StartAdditionalScopesUseCase,
    StartGoogleOAuthUseCase,
)
from src.domain.entities.google_integration import GoogleIntegration
from src.domain.entities.oauth_state import OAuthState
from src.infrastructure.external.google_oauth_client import (
    DEFAULT_SCOPES,
    TRANSCRIPT_SCOPES,
    GoogleTokenResponse,
    GoogleUserInfo,
)


class TestStartGoogleOAuthUseCase:
    """StartGoogleOAuthUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_generates_authorize_url_with_default_scopes(self) -> None:
        """デフォルトスコープでauthorize_urlが生成される"""
        # Arrange
        user_id = uuid4()
        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = "https://accounts.google.com/o/oauth2/v2/auth?..."

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.create = AsyncMock(side_effect=lambda x: x)

        with patch.object(
            google_auth_use_cases,
            "GoogleOAuthClient",
            return_value=mock_client,
        ):
            use_case = StartGoogleOAuthUseCase(mock_oauth_state_repository)

            # Act
            result = await use_case.execute(user_id)

            # Assert
            assert result.authorize_url == "https://accounts.google.com/o/oauth2/v2/auth?..."
            assert result.state is not None
            assert len(result.state) > 0
            mock_client.get_authorization_url.assert_called_once()
            call_args = mock_client.get_authorization_url.call_args
            assert call_args.kwargs["scopes"] == DEFAULT_SCOPES
            assert call_args.kwargs["include_granted_scopes"] is True
            mock_oauth_state_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_generates_authorize_url_with_custom_scopes(self) -> None:
        """カスタムスコープでauthorize_urlが生成される"""
        # Arrange
        user_id = uuid4()
        custom_scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = "https://accounts.google.com/..."

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.create = AsyncMock(side_effect=lambda x: x)

        with patch.object(
            google_auth_use_cases,
            "GoogleOAuthClient",
            return_value=mock_client,
        ):
            use_case = StartGoogleOAuthUseCase(mock_oauth_state_repository)

            # Act
            await use_case.execute(user_id, scopes=custom_scopes)

            # Assert
            call_args = mock_client.get_authorization_url.call_args
            assert call_args.kwargs["scopes"] == custom_scopes

    @pytest.mark.asyncio
    async def test_execute_stores_state_in_repository(self) -> None:
        """stateがリポジトリに保存される"""
        # Arrange
        user_id = uuid4()
        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = "https://accounts.google.com/..."

        created_oauth_state: OAuthState | None = None

        async def capture_create(oauth_state: OAuthState) -> OAuthState:
            nonlocal created_oauth_state
            created_oauth_state = oauth_state
            return oauth_state

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.create = AsyncMock(side_effect=capture_create)

        with patch.object(
            google_auth_use_cases,
            "GoogleOAuthClient",
            return_value=mock_client,
        ):
            use_case = StartGoogleOAuthUseCase(mock_oauth_state_repository)

            # Act
            result = await use_case.execute(user_id)

            # Assert
            assert created_oauth_state is not None
            assert created_oauth_state.state == result.state
            assert created_oauth_state.user_id == user_id
            assert created_oauth_state.provider == "google"
            assert created_oauth_state.scopes == DEFAULT_SCOPES

    @pytest.mark.asyncio
    async def test_execute_raises_when_oauth_not_configured(self) -> None:
        """OAuth未設定時にValueErrorが発生する"""
        # Arrange
        user_id = uuid4()
        mock_oauth_state_repository = AsyncMock()

        with patch.object(
            google_auth_use_cases,
            "GoogleOAuthClient",
            side_effect=ValueError("Google OAuth is not configured"),
        ):
            use_case = StartGoogleOAuthUseCase(mock_oauth_state_repository)

            # Act & Assert
            with pytest.raises(ValueError, match="Google OAuth is not configured"):
                await use_case.execute(user_id)


class TestHandleGoogleCallbackUseCase:
    """HandleGoogleCallbackUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_creates_new_integration_on_first_auth(self) -> None:
        """初回認証で新規GoogleIntegrationが作成される"""
        # Arrange
        user_id = uuid4()
        state = "valid_state"
        code = "auth_code"
        now = datetime.now(UTC)

        oauth_state = OAuthState(
            id=uuid4(),
            state=state,
            user_id=user_id,
            provider="google",
            scopes=DEFAULT_SCOPES,
            redirect_origin=None,
            expires_at=now + timedelta(minutes=5),
            created_at=now,
        )

        mock_token_response = GoogleTokenResponse(
            access_token="access_token",
            refresh_token="refresh_token",
            expires_in=3600,
            token_type="Bearer",
            scope="openid email profile",
        )
        mock_user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            picture=None,
        )
        mock_client = MagicMock()
        mock_client.exchange_code = AsyncMock(return_value=mock_token_response)
        mock_client.get_user_info = AsyncMock(return_value=mock_user_info)
        mock_client.parse_scopes = MagicMock(return_value=["openid", "email", "profile"])

        mock_repository = AsyncMock()
        mock_repository.get_by_email = AsyncMock(return_value=None)
        mock_repository.create = AsyncMock(side_effect=lambda x: x)

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.get_and_delete = AsyncMock(return_value=oauth_state)
        mock_oauth_state_repository.cleanup_expired = AsyncMock(return_value=0)

        with (
            patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client),
            patch.object(google_auth_use_cases, "encrypt_google_token", return_value="encrypted_token"),
        ):
            use_case = HandleGoogleCallbackUseCase(mock_repository, mock_oauth_state_repository)

            # Act
            integration, returned_state = await use_case.execute(code, state)

            # Assert
            assert integration.email == "test@example.com"
            assert integration.user_id == user_id
            assert integration.encrypted_refresh_token == "encrypted_token"
            assert returned_state.redirect_origin is None
            mock_repository.create.assert_called_once()
            mock_oauth_state_repository.cleanup_expired.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_updates_existing_integration(self) -> None:
        """既存連携の更新時にupdate_tokenとadd_scopesが呼ばれる"""
        # Arrange
        user_id = uuid4()
        state = "valid_state"
        code = "auth_code"
        now = datetime.now(UTC)

        oauth_state = OAuthState(
            id=uuid4(),
            state=state,
            user_id=user_id,
            provider="google",
            scopes=DEFAULT_SCOPES,
            redirect_origin=None,
            expires_at=now + timedelta(minutes=5),
            created_at=now,
        )

        existing_integration = GoogleIntegration(
            id=uuid4(),
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="old_token",
            granted_scopes=["openid"],
            created_at=datetime.now(),
            updated_at=None,
        )

        mock_token_response = GoogleTokenResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_in=3600,
            token_type="Bearer",
            scope="openid email profile",
        )
        mock_user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            picture=None,
        )
        mock_client = MagicMock()
        mock_client.exchange_code = AsyncMock(return_value=mock_token_response)
        mock_client.get_user_info = AsyncMock(return_value=mock_user_info)
        mock_client.parse_scopes = MagicMock(return_value=["openid", "email", "profile"])

        mock_repository = AsyncMock()
        mock_repository.get_by_email = AsyncMock(return_value=existing_integration)
        mock_repository.update = AsyncMock(side_effect=lambda x: x)

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.get_and_delete = AsyncMock(return_value=oauth_state)
        mock_oauth_state_repository.cleanup_expired = AsyncMock(return_value=0)

        with (
            patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client),
            patch.object(google_auth_use_cases, "encrypt_google_token", return_value="new_encrypted_token"),
        ):
            use_case = HandleGoogleCallbackUseCase(mock_repository, mock_oauth_state_repository)

            # Act
            integration, _ = await use_case.execute(code, state)

            # Assert
            assert integration.encrypted_refresh_token == "new_encrypted_token"
            mock_repository.update.assert_called_once()
            mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_raises_on_invalid_state(self) -> None:
        """無効なstateでValueErrorが発生する"""
        # Arrange
        mock_repository = AsyncMock()
        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.get_and_delete = AsyncMock(return_value=None)

        use_case = HandleGoogleCallbackUseCase(mock_repository, mock_oauth_state_repository)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid state parameter"):
            await use_case.execute("code", "invalid_state")

    @pytest.mark.asyncio
    async def test_execute_raises_on_expired_state(self) -> None:
        """期限切れstateでValueErrorが発生する"""
        # Arrange
        user_id = uuid4()
        state = "expired_state"
        now = datetime.now(UTC)

        # 期限切れのstate
        oauth_state = OAuthState(
            id=uuid4(),
            state=state,
            user_id=user_id,
            provider="google",
            scopes=DEFAULT_SCOPES,
            redirect_origin=None,
            expires_at=now - timedelta(minutes=1),  # Already expired
            created_at=now - timedelta(minutes=6),
        )

        mock_repository = AsyncMock()
        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.get_and_delete = AsyncMock(return_value=oauth_state)

        use_case = HandleGoogleCallbackUseCase(mock_repository, mock_oauth_state_repository)

        # Act & Assert
        with pytest.raises(ValueError, match="State expired"):
            await use_case.execute("code", state)

    @pytest.mark.asyncio
    async def test_execute_raises_when_no_refresh_token(self) -> None:
        """refresh_tokenがない場合にValueErrorが発生する"""
        # Arrange
        user_id = uuid4()
        state = "valid_state"
        now = datetime.now(UTC)

        oauth_state = OAuthState(
            id=uuid4(),
            state=state,
            user_id=user_id,
            provider="google",
            scopes=DEFAULT_SCOPES,
            redirect_origin=None,
            expires_at=now + timedelta(minutes=5),
            created_at=now,
        )

        mock_token_response = GoogleTokenResponse(
            access_token="access_token",
            refresh_token=None,  # No refresh token
            expires_in=3600,
            token_type="Bearer",
            scope="openid email profile",
        )
        mock_client = MagicMock()
        mock_client.exchange_code = AsyncMock(return_value=mock_token_response)

        mock_repository = AsyncMock()
        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.get_and_delete = AsyncMock(return_value=oauth_state)
        mock_oauth_state_repository.cleanup_expired = AsyncMock(return_value=0)

        with patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client):
            use_case = HandleGoogleCallbackUseCase(mock_repository, mock_oauth_state_repository)

            # Act & Assert
            with pytest.raises(ValueError, match="No refresh token received"):
                await use_case.execute("code", state)


class TestGetGoogleIntegrationsUseCase:
    """GetGoogleIntegrationsUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_returns_all_integrations(self) -> None:
        """ユーザーの全連携が取得される"""
        # Arrange
        user_id = uuid4()
        integrations = [
            GoogleIntegration(
                id=uuid4(),
                user_id=user_id,
                email="test1@example.com",
                encrypted_refresh_token="token1",
                granted_scopes=["openid"],
                created_at=datetime.now(),
                updated_at=None,
            ),
            GoogleIntegration(
                id=uuid4(),
                user_id=user_id,
                email="test2@example.com",
                encrypted_refresh_token="token2",
                granted_scopes=["openid"],
                created_at=datetime.now(),
                updated_at=None,
            ),
        ]
        mock_repository = AsyncMock()
        mock_repository.get_all = AsyncMock(return_value=integrations)

        use_case = GetGoogleIntegrationsUseCase(mock_repository)

        # Act
        result = await use_case.execute(user_id)

        # Assert
        assert len(result) == 2
        assert result[0].email == "test1@example.com"
        assert result[1].email == "test2@example.com"
        mock_repository.get_all.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_when_no_integrations(self) -> None:
        """連携がない場合は空リストが返される"""
        # Arrange
        user_id = uuid4()
        mock_repository = AsyncMock()
        mock_repository.get_all = AsyncMock(return_value=[])

        use_case = GetGoogleIntegrationsUseCase(mock_repository)

        # Act
        result = await use_case.execute(user_id)

        # Assert
        assert result == []


class TestDeleteGoogleIntegrationUseCase:
    """DeleteGoogleIntegrationUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_returns_true_on_success(self) -> None:
        """削除成功時にTrueが返される"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        mock_repository = AsyncMock()
        mock_repository.delete = AsyncMock(return_value=True)

        use_case = DeleteGoogleIntegrationUseCase(mock_repository)

        # Act
        result = await use_case.execute(integration_id, user_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(integration_id, user_id)

    @pytest.mark.asyncio
    async def test_execute_returns_false_when_not_found(self) -> None:
        """連携が見つからない場合にFalseが返される"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        mock_repository = AsyncMock()
        mock_repository.delete = AsyncMock(return_value=False)

        use_case = DeleteGoogleIntegrationUseCase(mock_repository)

        # Act
        result = await use_case.execute(integration_id, user_id)

        # Assert
        assert result is False


class TestStartAdditionalScopesUseCase:
    """StartAdditionalScopesUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_generates_url_with_additional_scopes(self) -> None:
        """追加スコープを含むauthorize_urlが生成される"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()
        additional_scopes = ["https://www.googleapis.com/auth/drive.readonly"]

        existing_integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["openid", "email"],
            created_at=datetime.now(),
            updated_at=None,
        )

        mock_repository = AsyncMock()
        mock_repository.get_by_id = AsyncMock(return_value=existing_integration)

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.create = AsyncMock(side_effect=lambda x: x)

        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = "https://accounts.google.com/..."

        with patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client):
            use_case = StartAdditionalScopesUseCase(mock_repository, mock_oauth_state_repository)

            # Act
            result = await use_case.execute(user_id, integration_id, additional_scopes)

            # Assert
            assert result.authorize_url == "https://accounts.google.com/..."
            assert result.state is not None
            # Verify combined scopes include both existing and additional
            call_args = mock_client.get_authorization_url.call_args
            combined_scopes = call_args.kwargs["scopes"]
            assert "openid" in combined_scopes
            assert "email" in combined_scopes
            assert "https://www.googleapis.com/auth/drive.readonly" in combined_scopes

    @pytest.mark.asyncio
    async def test_execute_raises_when_integration_not_found(self) -> None:
        """連携が見つからない場合にValueErrorが発生する"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()

        mock_repository = AsyncMock()
        mock_repository.get_by_id = AsyncMock(return_value=None)

        mock_oauth_state_repository = AsyncMock()

        use_case = StartAdditionalScopesUseCase(mock_repository, mock_oauth_state_repository)

        # Act & Assert
        with pytest.raises(ValueError, match="Integration not found"):
            await use_case.execute(user_id, integration_id)

    @pytest.mark.asyncio
    async def test_execute_uses_transcript_scopes_by_default(self) -> None:
        """追加スコープ未指定時はTRANSCRIPT_SCOPESが使用される"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()

        existing_integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["openid"],
            created_at=datetime.now(),
            updated_at=None,
        )

        mock_repository = AsyncMock()
        mock_repository.get_by_id = AsyncMock(return_value=existing_integration)

        mock_oauth_state_repository = AsyncMock()
        mock_oauth_state_repository.create = AsyncMock(side_effect=lambda x: x)

        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = "https://accounts.google.com/..."

        with patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client):
            use_case = StartAdditionalScopesUseCase(mock_repository, mock_oauth_state_repository)

            # Act
            await use_case.execute(user_id, integration_id, additional_scopes=None)

            # Assert
            call_args = mock_client.get_authorization_url.call_args
            combined_scopes = call_args.kwargs["scopes"]
            for scope in TRANSCRIPT_SCOPES:
                assert scope in combined_scopes


class TestRefreshGoogleTokenUseCase:
    """RefreshGoogleTokenUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_returns_new_access_token(self) -> None:
        """新しいアクセストークンが返される"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()

        existing_integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_refresh_token",
            granted_scopes=["openid"],
            created_at=datetime.now(),
            updated_at=None,
        )

        mock_token_response = GoogleTokenResponse(
            access_token="new_access_token",
            refresh_token="refresh_token",
            expires_in=3600,
            token_type="Bearer",
            scope="openid",
        )

        mock_repository = AsyncMock()
        mock_repository.get_by_id = AsyncMock(return_value=existing_integration)

        mock_client = MagicMock()
        mock_client.refresh_access_token = AsyncMock(return_value=mock_token_response)

        with (
            patch.object(google_auth_use_cases, "GoogleOAuthClient", return_value=mock_client),
            patch.object(
                google_auth_use_cases,
                "decrypt_google_token",
                return_value="decrypted_refresh_token",
            ),
        ):
            use_case = RefreshGoogleTokenUseCase(mock_repository)

            # Act
            result = await use_case.execute(user_id, integration_id)

            # Assert
            assert result == "new_access_token"
            mock_client.refresh_access_token.assert_called_once_with("decrypted_refresh_token")

    @pytest.mark.asyncio
    async def test_execute_raises_when_integration_not_found(self) -> None:
        """連携が見つからない場合にValueErrorが発生する"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()

        mock_repository = AsyncMock()
        mock_repository.get_by_id = AsyncMock(return_value=None)

        use_case = RefreshGoogleTokenUseCase(mock_repository)

        # Act & Assert
        with pytest.raises(ValueError, match="Integration not found"):
            await use_case.execute(user_id, integration_id)
