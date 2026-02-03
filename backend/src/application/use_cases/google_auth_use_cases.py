"""Use cases for Google OAuth and integration operations.

Following ADR-0003 authentication pattern with Incremental Authorization support.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.google_integration import GoogleIntegration
from src.domain.repositories.google_integration_repository import (
    GoogleIntegrationRepository,
)
from src.infrastructure.external.encryption import (
    decrypt_google_token,
    encrypt_google_token,
)
from src.infrastructure.external.google_oauth_client import (
    DEFAULT_SCOPES,
    TRANSCRIPT_SCOPES,
    GoogleOAuthClient,
)

# State store for CSRF protection (use Redis in production)
_state_store: dict[str, tuple[UUID, datetime, list[str]]] = {}


@dataclass
class OAuthStartResult:
    """OAuth開始結果."""

    authorize_url: str
    state: str


class StartGoogleOAuthUseCase:
    """Google OAuth開始ユースケース."""

    def execute(
        self,
        user_id: UUID,
        scopes: list[str] | None = None,
    ) -> OAuthStartResult:
        """OAuth認証URLを生成する.

        Args:
            user_id: ユーザーID.
            scopes: 要求するスコープ（省略時はデフォルトスコープ）.

        Returns:
            OAuthStartResult with authorize_url and state.

        Raises:
            ValueError: If Google OAuth is not configured.
        """
        client = GoogleOAuthClient()

        # state生成（CSRF対策）
        state = secrets.token_urlsafe(32)

        # 要求するスコープを決定
        request_scopes = scopes if scopes is not None else DEFAULT_SCOPES

        # stateをユーザーIDとスコープに紐付けて保存（5分間有効）
        _state_store[state] = (user_id, datetime.now(), request_scopes)

        authorize_url = client.get_authorization_url(
            state=state,
            scopes=request_scopes,
            include_granted_scopes=True,
        )

        return OAuthStartResult(authorize_url=authorize_url, state=state)


class HandleGoogleCallbackUseCase:
    """Google OAuthコールバックユースケース."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        code: str,
        state: str,
    ) -> GoogleIntegration:
        """OAuthコールバックを処理する.

        Args:
            code: OAuth認可コード.
            state: CSRFトークン.

        Returns:
            GoogleIntegration entity.

        Raises:
            ValueError: If state is invalid, expired, or token exchange fails.
        """
        # state検証（CSRF対策）
        if state not in _state_store:
            raise ValueError("Invalid state parameter")

        user_id, created_at, requested_scopes = _state_store.pop(state)

        # 5分以上経過していたら無効
        if (datetime.now() - created_at).seconds > 300:
            raise ValueError("State expired")

        # トークンを取得
        client = GoogleOAuthClient()
        token_response = await client.exchange_code(code)

        if not token_response.refresh_token:
            raise ValueError("No refresh token received. Please re-authenticate with consent.")

        # ユーザー情報を取得
        user_info = await client.get_user_info(token_response.access_token)

        # 許可されたスコープをパース
        granted_scopes = GoogleOAuthClient.parse_scopes(token_response.scope)

        # リフレッシュトークンを暗号化
        encrypted_token = encrypt_google_token(token_response.refresh_token)

        # 既存の連携を確認
        existing = await self.repository.get_by_email(user_id, user_info.email)

        if existing:
            # 既存の連携を更新
            existing.update_token(encrypted_token)
            existing.add_scopes(granted_scopes)
            return await self.repository.update(existing)

        # 新規作成
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=user_id,
            email=user_info.email,
            encrypted_refresh_token=encrypted_token,
            granted_scopes=granted_scopes,
            created_at=datetime.now(),
            updated_at=None,
        )
        return await self.repository.create(integration)


class GetGoogleIntegrationsUseCase:
    """Google連携一覧取得ユースケース."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, user_id: UUID) -> list[GoogleIntegration]:
        """ユーザーの全Google連携を取得する.

        Args:
            user_id: ユーザーID.

        Returns:
            List of GoogleIntegration entities.
        """
        return await self.repository.get_all(user_id)


class DeleteGoogleIntegrationUseCase:
    """Google連携削除ユースケース."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, integration_id: UUID, user_id: UUID) -> bool:
        """Google連携を削除する.

        Args:
            integration_id: 連携ID.
            user_id: ユーザーID.

        Returns:
            True if deleted, False if not found.
        """
        return await self.repository.delete(integration_id, user_id)


class StartAdditionalScopesUseCase:
    """追加スコープ認証ユースケース（Incremental Authorization）."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
        additional_scopes: list[str] | None = None,
    ) -> OAuthStartResult:
        """追加スコープの認証URLを生成する.

        Args:
            user_id: ユーザーID.
            integration_id: 連携ID.
            additional_scopes: 追加で要求するスコープ（省略時はトランスクリプトスコープ）.

        Returns:
            OAuthStartResult with authorize_url and state.

        Raises:
            ValueError: If integration not found or OAuth not configured.
        """
        # 連携の存在を確認
        integration = await self.repository.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # 追加スコープを決定
        scopes_to_request = additional_scopes if additional_scopes is not None else TRANSCRIPT_SCOPES

        # 既存スコープと合わせてリクエスト
        all_scopes = list(set(integration.granted_scopes + scopes_to_request))

        # OAuth開始
        start_use_case = StartGoogleOAuthUseCase()
        return start_use_case.execute(user_id, scopes=all_scopes)


class RefreshGoogleTokenUseCase:
    """Googleトークンリフレッシュユースケース."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
    ) -> str:
        """アクセストークンをリフレッシュして返す.

        Args:
            user_id: ユーザーID.
            integration_id: 連携ID.

        Returns:
            新しいアクセストークン.

        Raises:
            ValueError: If integration not found or refresh fails.
        """
        integration = await self.repository.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # リフレッシュトークンを復号
        refresh_token = decrypt_google_token(integration.encrypted_refresh_token)

        # アクセストークンをリフレッシュ
        client = GoogleOAuthClient()
        token_response = await client.refresh_access_token(refresh_token)

        return token_response.access_token


@dataclass
class SyncProviderTokenResult:
    """providerToken同期結果."""

    success: bool
    message: str
    integration_id: UUID | None = None


class SyncProviderTokenUseCase:
    """Supabase AuthのproviderTokenを同期するユースケース."""

    def __init__(self, repository: GoogleIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        email: str,
        provider_refresh_token: str | None,
        scopes: list[str] | None = None,
    ) -> SyncProviderTokenResult:
        """Supabase Authから取得したproviderTokenをgoogle_integrationsに保存する.

        Args:
            user_id: ユーザーID.
            email: Googleアカウントのメール.
            provider_refresh_token: Supabase Authから取得したrefresh_token.
            scopes: 許可されたスコープ.

        Returns:
            SyncProviderTokenResult.
        """
        if not provider_refresh_token:
            return SyncProviderTokenResult(
                success=False,
                message="No refresh token provided. Re-authenticate with consent.",
            )

        # 許可されたスコープを設定
        granted_scopes = scopes if scopes else DEFAULT_SCOPES

        # リフレッシュトークンを暗号化
        encrypted_token = encrypt_google_token(provider_refresh_token)

        # 既存の連携を確認
        existing = await self.repository.get_by_email(user_id, email)

        if existing:
            # 既存の連携を更新
            existing.update_token(encrypted_token)
            existing.add_scopes(granted_scopes)
            updated = await self.repository.update(existing)
            return SyncProviderTokenResult(
                success=True,
                message="Google integration updated",
                integration_id=updated.id,
            )

        # 新規作成
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=user_id,
            email=email,
            encrypted_refresh_token=encrypted_token,
            granted_scopes=granted_scopes,
            created_at=datetime.now(),
            updated_at=None,
        )
        created = await self.repository.create(integration)
        return SyncProviderTokenResult(
            success=True,
            message="Google integration created",
            integration_id=created.id,
        )
