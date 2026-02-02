"""RecurringMeeting repository implementation using Supabase.

Infrastructure layer implementation of RecurringMeetingRepository interface.
Following ADR-0001 clean architecture principles and RLS guidelines.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from src.domain.entities.recurring_meeting import (
    Attendee,
    MeetingFrequency,
    RecurringMeeting,
)
from src.domain.repositories.recurring_meeting_repository import (
    RecurringMeetingRepository,
)


class RecurringMeetingRepositoryImpl(RecurringMeetingRepository):
    """定例MTGリポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス.
        """
        self._client = client

    async def create(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを作成する."""
        data = self._to_dict(meeting)
        self._client.table("recurring_meetings").insert(data).execute()
        return meeting

    async def get_by_id(self, meeting_id: UUID, user_id: UUID) -> RecurringMeeting | None:
        """IDで定例MTGを取得する."""
        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("id", str(meeting_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_by_google_event_id(
        self,
        user_id: UUID,
        google_event_id: str,
    ) -> RecurringMeeting | None:
        """Google Event IDで定例MTGを取得する."""
        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("google_event_id", google_event_id)
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_all(self, user_id: UUID) -> list[RecurringMeeting]:
        """ユーザーの全定例MTGを取得する."""
        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("user_id", str(user_id))
            .order("next_occurrence", desc=False)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def get_list_by_agent_id(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> list[RecurringMeeting]:
        """エージェントに紐付けられた定例MTG一覧を取得する."""
        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("agent_id", str(agent_id))
            .eq("user_id", str(user_id))  # RLS: user_idフィルタ必須
            .order("next_occurrence", desc=False)
            .execute()
        )
        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def link_to_agent(
        self,
        recurring_meeting_id: UUID,
        agent_id: UUID,
        user_id: UUID,
    ) -> RecurringMeeting:
        """定例MTGをエージェントに紐付ける."""
        data = {
            "agent_id": str(agent_id),
            "updated_at": datetime.now().isoformat(),
        }
        result = (
            self._client.table("recurring_meetings")
            .update(data)
            .eq("id", str(recurring_meeting_id))
            .eq("user_id", str(user_id))  # RLS: user_idフィルタ必須
            .execute()
        )
        if not result.data:
            raise ValueError("Recurring meeting not found or access denied")
        return self._to_entity(dict(result.data[0]))  # type: ignore[arg-type]

    async def unlink_from_agent(
        self,
        recurring_meeting_id: UUID,
        user_id: UUID,
    ) -> None:
        """定例MTGとエージェントの紐付けを解除する."""
        data = {
            "agent_id": None,
            "updated_at": datetime.now().isoformat(),
        }
        (
            self._client.table("recurring_meetings")
            .update(data)
            .eq("id", str(recurring_meeting_id))
            .eq("user_id", str(user_id))  # RLS: user_idフィルタ必須
            .execute()
        )

    async def get_unlinked(self, user_id: UUID) -> list[RecurringMeeting]:
        """エージェントに紐付けられていない定例MTGを取得する."""
        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("user_id", str(user_id))
            .is_("agent_id", "null")
            .order("next_occurrence", desc=False)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def update(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを更新する."""
        data = {
            "title": meeting.title,
            "rrule": meeting.rrule,
            "frequency": meeting.frequency.value,
            "attendees": [{"email": a.email, "name": a.name} for a in meeting.attendees],
            "next_occurrence": meeting.next_occurrence.isoformat(),
            "agent_id": str(meeting.agent_id) if meeting.agent_id else None,
            "updated_at": datetime.now().isoformat(),
        }
        (
            self._client.table("recurring_meetings")
            .update(data)
            .eq("id", str(meeting.id))
            .eq("user_id", str(meeting.user_id))
            .execute()
        )
        return meeting

    async def delete(self, meeting_id: UUID, user_id: UUID) -> bool:
        """定例MTGを削除する."""
        result = (
            self._client.table("recurring_meetings")
            .delete()
            .eq("id", str(meeting_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    async def upsert(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを作成または更新する."""
        existing = await self.get_by_google_event_id(meeting.user_id, meeting.google_event_id)

        if existing:
            existing.title = meeting.title
            existing.rrule = meeting.rrule
            existing.frequency = meeting.frequency
            existing.attendees = meeting.attendees
            existing.next_occurrence = meeting.next_occurrence
            return await self.update(existing)
        return await self.create(meeting)

    def _to_dict(self, meeting: RecurringMeeting) -> dict[str, Any]:
        """エンティティをDB用辞書に変換する."""
        return {
            "id": str(meeting.id),
            "user_id": str(meeting.user_id),
            "google_event_id": meeting.google_event_id,
            "title": meeting.title,
            "rrule": meeting.rrule,
            "frequency": meeting.frequency.value,
            "attendees": [{"email": a.email, "name": a.name} for a in meeting.attendees],
            "next_occurrence": meeting.next_occurrence.isoformat(),
            "agent_id": str(meeting.agent_id) if meeting.agent_id else None,
            "created_at": meeting.created_at.isoformat(),
        }

    def _to_entity(self, data: dict[str, Any]) -> RecurringMeeting:
        """DB結果をRecurringMeetingエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")
        next_occurrence_str = data["next_occurrence"]
        attendees_raw = data.get("attendees", [])
        agent_id_raw = data.get("agent_id")

        attendees: list[Attendee] = [
            Attendee(
                email=str(a.get("email", "")),
                name=a.get("name"),
            )
            for a in (attendees_raw or [])
            if isinstance(a, dict)
        ]

        return RecurringMeeting(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            google_event_id=str(data["google_event_id"]),
            title=str(data["title"]),
            rrule=str(data["rrule"]),
            frequency=MeetingFrequency(str(data["frequency"])),
            attendees=attendees,
            next_occurrence=(
                datetime.fromisoformat(str(next_occurrence_str))
                if isinstance(next_occurrence_str, str)
                else datetime.now()
            ),
            agent_id=UUID(str(agent_id_raw)) if agent_id_raw else None,
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )
