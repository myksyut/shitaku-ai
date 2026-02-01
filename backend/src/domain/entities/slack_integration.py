"""SlackIntegration and SlackMessage entities for domain layer.

Pure Python entities without external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SlackIntegration:
    """Slack連携を表すエンティティ.

    Attributes:
        id: Unique identifier for the integration.
        user_id: ID of the owning user.
        workspace_id: Slack workspace ID (e.g., T01234567).
        workspace_name: Human-readable workspace name.
        encrypted_access_token: AES-256-GCM encrypted OAuth access token.
        created_at: Timestamp when the integration was created.
        updated_at: Timestamp when the integration was last updated.
    """

    id: UUID
    user_id: UUID
    workspace_id: str
    workspace_name: str
    encrypted_access_token: str
    created_at: datetime
    updated_at: datetime | None

    def update_token(self, encrypted_token: str) -> None:
        """アクセストークンを更新.

        Args:
            encrypted_token: New encrypted access token.
        """
        self.encrypted_access_token = encrypted_token
        self.updated_at = datetime.now()


@dataclass
class SlackMessage:
    """Slackメッセージを表すエンティティ.

    Attributes:
        id: Unique identifier for the message.
        integration_id: ID of the SlackIntegration this message belongs to.
        channel_id: Slack channel ID (e.g., C01234567).
        message_ts: Slack's unique timestamp identifier for the message.
        user_name: Display name of the message author.
        text: Message content.
        posted_at: Timestamp when the message was posted.
    """

    id: UUID
    integration_id: UUID
    channel_id: str
    message_ts: str
    user_name: str
    text: str
    posted_at: datetime

    def to_display_text(self) -> str:
        """表示用テキストを生成.

        Returns:
            Formatted string for display: [YYYY-MM-DD HH:MM] user_name: text
        """
        return f"[{self.posted_at.strftime('%Y-%m-%d %H:%M')}] {self.user_name}: {self.text}"
