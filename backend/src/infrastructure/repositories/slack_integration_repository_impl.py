"""SlackIntegration repository implementation using Supabase.

Infrastructure layer implementation of SlackIntegrationRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.slack_integration import SlackIntegration, SlackMessage
from src.domain.repositories.slack_integration_repository import (
    SlackIntegrationRepository,
)
from src.infrastructure.external.supabase_client import get_supabase_client


class SlackIntegrationRepositoryImpl(SlackIntegrationRepository):
    """Slack連携リポジトリのSupabase実装."""

    def __init__(self) -> None:
        """リポジトリを初期化する."""
        self._client = get_supabase_client()

    async def create(self, integration: SlackIntegration) -> SlackIntegration:
        """Slack連携を作成する."""
        if self._client is None:
            return integration

        data = {
            "id": str(integration.id),
            "user_id": str(integration.user_id),
            "workspace_id": integration.workspace_id,
            "workspace_name": integration.workspace_name,
            "encrypted_access_token": integration.encrypted_access_token,
            "created_at": integration.created_at.isoformat(),
        }
        self._client.table("slack_integrations").insert(data).execute()
        return integration

    async def get_by_id(self, integration_id: UUID, user_id: UUID) -> SlackIntegration | None:
        """IDでSlack連携を取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_by_workspace(
        self,
        user_id: UUID,
        workspace_id: str,
    ) -> SlackIntegration | None:
        """ワークスペースIDでSlack連携を取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("workspace_id", workspace_id)
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_all(self, user_id: UUID) -> list[SlackIntegration]:
        """ユーザーの全Slack連携を取得する."""
        if self._client is None:
            return []

        result = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def update(self, integration: SlackIntegration) -> SlackIntegration:
        """Slack連携を更新する."""
        if self._client is None:
            return integration

        data = {
            "workspace_name": integration.workspace_name,
            "encrypted_access_token": integration.encrypted_access_token,
            "updated_at": datetime.now().isoformat(),
        }
        (
            self._client.table("slack_integrations")
            .update(data)
            .eq("id", str(integration.id))
            .eq("user_id", str(integration.user_id))
            .execute()
        )
        return integration

    async def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Slack連携を削除する."""
        if self._client is None:
            return False

        result = (
            self._client.table("slack_integrations")
            .delete()
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    async def save_messages(self, messages: list[SlackMessage]) -> None:
        """Slackメッセージを保存する."""
        if self._client is None or not messages:
            return

        data = [
            {
                "id": str(msg.id),
                "integration_id": str(msg.integration_id),
                "channel_id": msg.channel_id,
                "message_ts": msg.message_ts,
                "user_name": msg.user_name,
                "text": msg.text,
                "posted_at": msg.posted_at.isoformat(),
            }
            for msg in messages
        ]
        # upsertで重複を避ける
        self._client.table("slack_messages").upsert(data, on_conflict="integration_id,channel_id,message_ts").execute()

    async def get_messages_by_channel(
        self,
        integration_id: UUID,
        channel_id: str,
        after: datetime,
        before: datetime | None = None,
    ) -> list[SlackMessage]:
        """期間指定でSlackメッセージを取得する."""
        if self._client is None:
            return []

        query = (
            self._client.table("slack_messages")
            .select("*")
            .eq("integration_id", str(integration_id))
            .eq("channel_id", channel_id)
            .gte("posted_at", after.isoformat())
        )

        if before:
            query = query.lt("posted_at", before.isoformat())

        result = query.order("posted_at", desc=False).execute()

        return [self._to_message_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    def _to_entity(self, data: dict[str, Any]) -> SlackIntegration:
        """DB結果をSlackIntegrationエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")

        return SlackIntegration(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            workspace_id=str(data["workspace_id"]),
            workspace_name=str(data["workspace_name"]),
            encrypted_access_token=str(data["encrypted_access_token"]),
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )

    def _to_message_entity(self, data: dict[str, Any]) -> SlackMessage:
        """DB結果をSlackMessageエンティティに変換する."""
        posted_at_str = data["posted_at"]

        return SlackMessage(
            id=UUID(str(data["id"])),
            integration_id=UUID(str(data["integration_id"])),
            channel_id=str(data["channel_id"]),
            message_ts=str(data["message_ts"]),
            user_name=str(data["user_name"]),
            text=str(data["text"]),
            posted_at=(
                datetime.fromisoformat(str(posted_at_str)) if isinstance(posted_at_str, str) else datetime.now()
            ),
        )
