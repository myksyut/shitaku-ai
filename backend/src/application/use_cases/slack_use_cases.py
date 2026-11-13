"""Use cases for Slack OAuth and integration operations."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from pydantic import TypeAdapter

from src.config import settings
from src.domain.entities.oauth_state import OAuthState
from src.domain.entities.slack_integration import SlackIntegration
from src.domain.repositories.oauth_state_repository import OAuthStateRepository
from src.domain.repositories.slack_integration_repository import (
    SlackIntegrationRepository,
)
from src.infrastructure.external.encryption import encrypt_token
from src.infrastructure.external.series_credentials import SeriesCredentials
from src.infrastructure.external.slack_client import SlackChannel


@dataclass
class OAuthStartResult:
    """OAuth開始結果."""

    authorize_url: str
    state: str


class StartSlackOAuthUseCase:
    """Slack OAuth開始ユースケース."""

    # OAuth stateの有効期限（5分）
    STATE_EXPIRES_MINUTES = 5

    def __init__(self, oauth_state_repository: OAuthStateRepository) -> None:
        """Initialize use case with repository.

        Args:
            oauth_state_repository: OAuth state repository.
        """
        self.oauth_state_repository = oauth_state_repository

    def execute(self, user_id: UUID, redirect_origin: str | None = None) -> OAuthStartResult:
        """OAuth認証URLを生成する.

        Args:
            user_id: ユーザーID.
            redirect_origin: callback後のリダイレクト先オリジン.

        Returns:
            OAuthStartResult with authorize_url and state.

        Raises:
            ValueError: If Slack OAuth is not configured.
        """
        if not settings.SLACK_CLIENT_ID or not settings.SLACK_REDIRECT_URI:
            raise ValueError("Slack OAuth is not configured")

        # state生成（CSRF対策）
        state = secrets.token_urlsafe(32)
        now = datetime.now(UTC)

        # Slack OAuth scopes
        scopes = ["channels:read", "channels:history", "groups:read", "groups:history", "users:read"]

        # OAuthStateエンティティを作成してリポジトリに保存
        oauth_state = OAuthState(
            id=uuid4(),
            state=state,
            user_id=user_id,
            provider="slack",
            scopes=scopes,
            redirect_origin=redirect_origin,
            expires_at=now + timedelta(minutes=self.STATE_EXPIRES_MINUTES),
            created_at=now,
        )
        self.oauth_state_repository.create(oauth_state)

        # Slack OAuth URLを構築
        params = {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": ",".join(scopes),
            "redirect_uri": settings.SLACK_REDIRECT_URI,
            "state": state,
        }

        authorize_url = f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"

        return OAuthStartResult(authorize_url=authorize_url, state=state)


class HandleSlackCallbackUseCase:
    """Slack OAuthコールバックユースケース."""

    def __init__(
        self,
        repository: SlackIntegrationRepository,
        oauth_state_repository: OAuthStateRepository,
    ) -> None:
        """Initialize use case with repositories.

        Args:
            repository: Slack integration repository.
            oauth_state_repository: OAuth state repository.
        """
        self.repository = repository
        self.oauth_state_repository = oauth_state_repository

    def execute(
        self,
        code: str,
        state: str,
    ) -> tuple[SlackIntegration, OAuthState]:
        """OAuthコールバックを処理する.

        Args:
            code: OAuth認可コード.
            state: CSRFトークン.

        Returns:
            Tuple of (SlackIntegration entity, OAuthState with redirect_origin).

        Raises:
            ValueError: If state is invalid or expired.
        """
        # state検証（CSRF対策）- リポジトリから取得と同時に削除
        oauth_state = self.oauth_state_repository.get_and_delete(state)

        if oauth_state is None:
            raise ValueError("Invalid state parameter")

        # 有効期限チェック
        if oauth_state.is_expired():
            raise ValueError("State expired")

        user_id = oauth_state.user_id

        # 期限切れstateのクリーンアップ（非同期で実行）
        self.oauth_state_repository.cleanup_expired()

        # アクセストークンを取得
        token_response = self._exchange_code(code)

        team_data = token_response.get("team")
        if not isinstance(team_data, dict):
            raise ValueError("Invalid Slack response: team data missing")
        team_data = TypeAdapter(dict[str, object]).validate_python(team_data)

        workspace_id = str(team_data.get("id") or "")
        workspace_name = str(team_data.get("name") or "")
        access_token = str(token_response.get("access_token") or "")

        if not workspace_id or not access_token:
            raise ValueError("Invalid Slack response: missing required fields")

        # トークンを暗号化
        encrypted_token = encrypt_token(access_token)

        # 既存の連携を確認
        existing = self.repository.get_by_workspace(user_id, workspace_id)

        if existing:
            # 既存の連携を更新
            existing.update_token(encrypted_token)
            return self.repository.update(existing), oauth_state

        # 新規作成
        integration = SlackIntegration(
            id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            encrypted_access_token=encrypted_token,
            created_at=datetime.now(),
            updated_at=None,
        )
        return self.repository.create(integration), oauth_state

    def _exchange_code(self, code: str) -> dict[str, object]:
        """認可コードをアクセストークンに交換する."""
        if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET:
            raise ValueError("Slack OAuth is not configured")

        with httpx.Client() as client:
            response = client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.SLACK_REDIRECT_URI,
                },
            )

            data: dict[str, object] = response.json()
            if not data.get("ok"):
                raise ValueError(f"Slack OAuth failed: {data.get('error')}")

            return data


class GetSlackIntegrationsUseCase:
    """Slack連携一覧取得ユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    def execute(self, user_id: UUID) -> list[SlackIntegration]:
        """ユーザーの全Slack連携を取得する.

        Args:
            user_id: ユーザーID.

        Returns:
            List of SlackIntegration entities.
        """
        return self.repository.get_all(user_id)


class DeleteSlackIntegrationUseCase:
    """Slack連携削除ユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    def execute(self, integration_id: UUID, user_id: UUID) -> bool:
        """Slack連携を削除する.

        Args:
            integration_id: 連携ID.
            user_id: ユーザーID.

        Returns:
            True if deleted, False if not found.
        """
        return self.repository.delete(integration_id, user_id)


class GetSlackChannelsUseCase:
    """List channels from the explicitly selected personal integration."""

    def __init__(self, credentials: SeriesCredentials) -> None:
        self.credentials = credentials

    def execute(self, user_id: UUID, integration_id: UUID) -> list[SlackChannel]:
        """List channels of the caller's Slack integration."""
        client = self.credentials.slack_for_user(user_id, integration_id)
        return client.get_channels()
