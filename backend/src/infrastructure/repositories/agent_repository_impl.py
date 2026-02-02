"""Agent repository implementation using Supabase.

Infrastructure layer implementation of AgentRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.agent import Agent
from src.domain.repositories.agent_repository import AgentRepository
from src.infrastructure.external.supabase_client import get_supabase_client


class AgentRepositoryImpl(AgentRepository):
    """エージェントリポジトリのSupabase実装."""

    def __init__(self) -> None:
        """リポジトリを初期化する."""
        self._client = get_supabase_client()

    def get_by_id(self, agent_id: UUID, user_id: UUID) -> Agent | None:
        """IDでエージェントを取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("agents")
            .select("*")
            .eq("id", str(agent_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    def get_all(self, user_id: UUID) -> list[Agent]:
        """ユーザーの全エージェントを取得する."""
        if self._client is None:
            return []

        result = (
            self._client.table("agents")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    def create(self, agent: Agent) -> Agent:
        """エージェントを作成する."""
        if self._client is None:
            return agent

        data = {
            "id": str(agent.id),
            "user_id": str(agent.user_id),
            "name": agent.name,
            "description": agent.description,
            "slack_channel_id": agent.slack_channel_id,
            "created_at": agent.created_at.isoformat(),
        }
        self._client.table("agents").insert(data).execute()
        return agent

    def update(self, agent: Agent) -> Agent:
        """エージェントを更新する."""
        if self._client is None:
            return agent

        data = {
            "name": agent.name,
            "description": agent.description,
            "slack_channel_id": agent.slack_channel_id,
            "updated_at": datetime.now().isoformat(),
        }
        self._client.table("agents").update(data).eq("id", str(agent.id)).eq("user_id", str(agent.user_id)).execute()
        return agent

    def delete(self, agent_id: UUID, user_id: UUID) -> bool:
        """エージェントを削除する."""
        if self._client is None:
            return False

        result = self._client.table("agents").delete().eq("id", str(agent_id)).eq("user_id", str(user_id)).execute()
        return len(result.data) > 0

    def exists(self, agent_id: UUID, user_id: UUID) -> bool:
        """エージェントの存在を確認する."""
        if self._client is None:
            return False

        result = self._client.table("agents").select("id").eq("id", str(agent_id)).eq("user_id", str(user_id)).execute()
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> Agent:
        """DB結果をエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")

        return Agent(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            name=str(data["name"]),
            description=str(data["description"]) if data.get("description") else None,
            slack_channel_id=(str(data["slack_channel_id"]) if data.get("slack_channel_id") else None),
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )
