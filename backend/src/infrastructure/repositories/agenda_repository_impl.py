"""Agenda repository implementation using Supabase.

Infrastructure layer implementation of AgendaRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from src.domain.entities.agenda import Agenda
from src.domain.repositories.agenda_repository import AgendaRepository


class AgendaRepositoryImpl(AgendaRepository):
    """アジェンダリポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス.
        """
        self._client = client

    async def create(self, agenda: Agenda) -> Agenda:
        """アジェンダを作成する."""
        if self._client is None:
            return agenda

        data = {
            "id": str(agenda.id),
            "agent_id": str(agenda.agent_id),
            "user_id": str(agenda.user_id),
            "content": agenda.content,
            "source_knowledge_id": str(agenda.source_knowledge_id) if agenda.source_knowledge_id else None,
            "generated_at": agenda.generated_at.isoformat(),
            "created_at": agenda.created_at.isoformat(),
        }
        self._client.table("agendas").insert(data).execute()
        return agenda

    async def get_by_id(self, agenda_id: UUID, user_id: UUID) -> Agenda | None:
        """IDでアジェンダを取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("agendas")
            .select("*")
            .eq("id", str(agenda_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Agenda]:
        """エージェントのアジェンダ一覧を取得する."""
        if self._client is None:
            return []

        query = (
            self._client.table("agendas")
            .select("*")
            .eq("agent_id", str(agent_id))
            .eq("user_id", str(user_id))
            .order("generated_at", desc=True)
        )

        if limit is not None:
            query = query.limit(limit)

        result = query.execute()
        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def update(self, agenda: Agenda) -> Agenda:
        """アジェンダを更新する."""
        if self._client is None:
            return agenda

        data = {
            "content": agenda.content,
            "updated_at": datetime.now().isoformat(),
        }
        self._client.table("agendas").update(data).eq("id", str(agenda.id)).execute()
        return agenda

    async def delete(self, agenda_id: UUID, user_id: UUID) -> bool:
        """アジェンダを削除する."""
        if self._client is None:
            return False

        result = self._client.table("agendas").delete().eq("id", str(agenda_id)).eq("user_id", str(user_id)).execute()
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> Agenda:
        """DB結果をエンティティに変換する."""
        generated_at_str = data["generated_at"]
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")
        source_knowledge_id_str = data.get("source_knowledge_id")

        return Agenda(
            id=UUID(str(data["id"])),
            agent_id=UUID(str(data["agent_id"])),
            user_id=UUID(str(data["user_id"])),
            content=str(data["content"]),
            source_knowledge_id=UUID(str(source_knowledge_id_str)) if source_knowledge_id_str else None,
            generated_at=(
                datetime.fromisoformat(str(generated_at_str)) if isinstance(generated_at_str, str) else datetime.now()
            ),
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )
