"""Personal Slack integration credentials."""

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
