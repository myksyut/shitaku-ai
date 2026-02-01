"""Use cases for Slack OAuth and integration operations."""

import secrets
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx

from src.config import settings
from src.domain.entities.slack_integration import SlackIntegration
from src.domain.repositories.slack_integration_repository import (
    SlackIntegrationRepository,
)
from src.infrastructure.external.encryption import decrypt_token, encrypt_token
from src.infrastructure.external.slack_client import (
    SlackChannel,
    SlackClient,
    SlackMessageData,
)

# stateを一時保存するためのストア（本番ではRedis等を使用）
_state_store: dict[str, tuple[UUID, datetime]] = {}


@dataclass
class OAuthStartResult:
    """OAuth開始結果."""

    authorize_url: str
    state: str


class StartSlackOAuthUseCase:
    """Slack OAuth開始ユースケース."""

    def execute(self, user_id: UUID) -> OAuthStartResult:
        """OAuth認証URLを生成する.

        Args:
            user_id: ユーザーID.

        Returns:
            OAuthStartResult with authorize_url and state.

        Raises:
            ValueError: If Slack OAuth is not configured.
        """
        if not settings.SLACK_CLIENT_ID or not settings.SLACK_REDIRECT_URI:
            raise ValueError("Slack OAuth is not configured")

        # state生成（CSRF対策）
        state = secrets.token_urlsafe(32)

        # stateをユーザーIDと紐付けて保存（5分間有効）
        _state_store[state] = (user_id, datetime.now())

        # Slack OAuth URLを構築
        params = {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": "channels:read,channels:history,users:read",
            "redirect_uri": settings.SLACK_REDIRECT_URI,
            "state": state,
        }

        authorize_url = f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"

        return OAuthStartResult(authorize_url=authorize_url, state=state)


class HandleSlackCallbackUseCase:
    """Slack OAuthコールバックユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        code: str,
        state: str,
    ) -> SlackIntegration:
        """OAuthコールバックを処理する.

        Args:
            code: OAuth認可コード.
            state: CSRFトークン.

        Returns:
            SlackIntegration entity.

        Raises:
            ValueError: If state is invalid or expired.
        """
        # state検証（CSRF対策）
        if state not in _state_store:
            raise ValueError("Invalid state parameter")

        user_id, created_at = _state_store.pop(state)

        # 5分以上経過していたら無効
        if (datetime.now() - created_at).seconds > 300:
            raise ValueError("State expired")

        # アクセストークンを取得
        token_response = await self._exchange_code(code)

        team_data = token_response.get("team", {})
        if not isinstance(team_data, dict):
            raise ValueError("Invalid Slack response: team data missing")

        workspace_id = str(team_data.get("id", ""))
        workspace_name = str(team_data.get("name", ""))
        access_token = str(token_response.get("access_token", ""))

        if not workspace_id or not access_token:
            raise ValueError("Invalid Slack response: missing required fields")

        # トークンを暗号化
        encrypted_token = encrypt_token(access_token)

        # 既存の連携を確認
        existing = await self.repository.get_by_workspace(user_id, workspace_id)

        if existing:
            # 既存の連携を更新
            existing.update_token(encrypted_token)
            return await self.repository.update(existing)

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
        return await self.repository.create(integration)

    async def _exchange_code(self, code: str) -> dict[str, object]:
        """認可コードをアクセストークンに交換する."""
        if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET:
            raise ValueError("Slack OAuth is not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
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

    async def execute(self, user_id: UUID) -> list[SlackIntegration]:
        """ユーザーの全Slack連携を取得する.

        Args:
            user_id: ユーザーID.

        Returns:
            List of SlackIntegration entities.
        """
        return await self.repository.get_all(user_id)


class DeleteSlackIntegrationUseCase:
    """Slack連携削除ユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, integration_id: UUID, user_id: UUID) -> bool:
        """Slack連携を削除する.

        Args:
            integration_id: 連携ID.
            user_id: ユーザーID.

        Returns:
            True if deleted, False if not found.
        """
        return await self.repository.delete(integration_id, user_id)


class GetSlackChannelsUseCase:
    """Slackチャンネル一覧取得ユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
    ) -> list[SlackChannel]:
        """Slackチャンネル一覧を取得する.

        Args:
            user_id: ユーザーID.
            integration_id: 連携ID.

        Returns:
            List of SlackChannel objects.

        Raises:
            ValueError: If integration not found or token invalid.
        """
        integration = await self.repository.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # トークンを復号
        token = decrypt_token(integration.encrypted_access_token)

        # Slackクライアントでチャンネル取得
        client = SlackClient(token)

        if not client.verify_token():
            raise ValueError("Slack token is invalid. Please re-authenticate.")

        return client.get_channels()


class GetSlackMessagesUseCase:
    """Slackメッセージ取得ユースケース."""

    def __init__(self, repository: SlackIntegrationRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
        channel_id: str,
        oldest: datetime,
        latest: datetime | None = None,
    ) -> list[SlackMessageData]:
        """期間指定でSlackメッセージを取得する.

        Args:
            user_id: ユーザーID.
            integration_id: 連携ID.
            channel_id: チャンネルID.
            oldest: 取得開始日時.
            latest: 取得終了日時（省略時は現在）.

        Returns:
            List of SlackMessageData objects.

        Raises:
            ValueError: If integration not found or token invalid.
        """
        integration = await self.repository.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # トークンを復号
        token = decrypt_token(integration.encrypted_access_token)

        # Slackクライアントでメッセージ取得
        client = SlackClient(token)

        if not client.verify_token():
            raise ValueError("Slack token is invalid. Please re-authenticate.")

        return client.get_messages(channel_id, oldest, latest)
