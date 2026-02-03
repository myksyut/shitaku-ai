"""KnowledgeRepository implementation using Supabase.

Infrastructure layer implementation of KnowledgeRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from supabase import Client

from src.domain.entities.knowledge import Knowledge
from src.domain.repositories.knowledge_repository import KnowledgeRepository


class KnowledgeRepositoryImpl(KnowledgeRepository):
    """ナレッジリポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス
        """
        self.client = client

    async def create(self, knowledge: Knowledge) -> Knowledge:
        """ナレッジを作成する."""
        data = {
            "id": str(knowledge.id),
            "agent_id": str(knowledge.agent_id),
            "user_id": str(knowledge.user_id),
            "original_text": knowledge.original_text,
            "normalized_text": knowledge.normalized_text,
            "meeting_date": knowledge.meeting_date.isoformat(),
            "created_at": knowledge.created_at.isoformat(),
        }
        self.client.table("knowledge").insert(data).execute()
        return knowledge

    async def get_by_id(self, knowledge_id: UUID, user_id: UUID) -> Knowledge | None:
        """IDでナレッジを取得する."""
        result = (
            self.client.table("knowledge")
            .select("*")
            .eq("id", str(knowledge_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        return self._to_entity(cast(dict[str, Any], result.data))

    async def get_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Knowledge]:
        """エージェントのナレッジ一覧を取得する."""
        query = (
            self.client.table("knowledge")
            .select("*")
            .eq("agent_id", str(agent_id))
            .eq("user_id", str(user_id))
            .order("meeting_date", desc=True)
        )

        if limit is not None:
            query = query.limit(limit)

        result = query.execute()
        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    async def get_latest_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> Knowledge | None:
        """エージェントの最新ナレッジを取得する."""
        result = (
            self.client.table("knowledge")
            .select("*")
            .eq("agent_id", str(agent_id))
            .eq("user_id", str(user_id))
            .order("meeting_date", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return self._to_entity(cast(dict[str, Any], result.data[0]))

    async def delete(self, knowledge_id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除する."""
        result = (
            self.client.table("knowledge").delete().eq("id", str(knowledge_id)).eq("user_id", str(user_id)).execute()
        )
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> Knowledge:
        """DB結果をエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")
        meeting_date_str = data["meeting_date"]

        # Handle timezone-aware ISO format
        created_at = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
        meeting_date = datetime.fromisoformat(str(meeting_date_str).replace("Z", "+00:00"))
        updated_at = None
        if updated_at_str:
            updated_at = datetime.fromisoformat(str(updated_at_str).replace("Z", "+00:00"))

        return Knowledge(
            id=UUID(str(data["id"])),
            agent_id=UUID(str(data["agent_id"])),
            user_id=UUID(str(data["user_id"])),
            original_text=str(data["original_text"]),
            normalized_text=str(data["normalized_text"]),
            meeting_date=meeting_date,
            created_at=created_at,
            updated_at=updated_at,
        )
