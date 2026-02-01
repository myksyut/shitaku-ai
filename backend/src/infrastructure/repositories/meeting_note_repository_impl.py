"""MeetingNoteRepository implementation using Supabase.

Infrastructure layer implementation of MeetingNoteRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from supabase import Client

from src.domain.entities.meeting_note import MeetingNote
from src.domain.repositories.meeting_note_repository import MeetingNoteRepository


class MeetingNoteRepositoryImpl(MeetingNoteRepository):
    """議事録リポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス
        """
        self.client = client

    async def create(self, note: MeetingNote) -> MeetingNote:
        """議事録を作成する."""
        data = {
            "id": str(note.id),
            "agent_id": str(note.agent_id),
            "user_id": str(note.user_id),
            "original_text": note.original_text,
            "normalized_text": note.normalized_text,
            "meeting_date": note.meeting_date.isoformat(),
            "created_at": note.created_at.isoformat(),
        }
        self.client.table("meeting_notes").insert(data).execute()
        return note

    async def get_by_id(self, note_id: UUID, user_id: UUID) -> MeetingNote | None:
        """IDで議事録を取得する."""
        result = (
            self.client.table("meeting_notes")
            .select("*")
            .eq("id", str(note_id))
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
    ) -> list[MeetingNote]:
        """エージェントの議事録一覧を取得する."""
        query = (
            self.client.table("meeting_notes")
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
    ) -> MeetingNote | None:
        """エージェントの最新議事録を取得する."""
        result = (
            self.client.table("meeting_notes")
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

    async def delete(self, note_id: UUID, user_id: UUID) -> bool:
        """議事録を削除する."""
        result = (
            self.client.table("meeting_notes").delete().eq("id", str(note_id)).eq("user_id", str(user_id)).execute()
        )
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> MeetingNote:
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

        return MeetingNote(
            id=UUID(str(data["id"])),
            agent_id=UUID(str(data["agent_id"])),
            user_id=UUID(str(data["user_id"])),
            original_text=str(data["original_text"]),
            normalized_text=str(data["normalized_text"]),
            meeting_date=meeting_date,
            created_at=created_at,
            updated_at=updated_at,
        )
