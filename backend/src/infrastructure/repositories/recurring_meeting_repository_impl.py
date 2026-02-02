"""RecurringMeeting repository implementation using Supabase.

Infrastructure layer implementation of RecurringMeetingRepository interface.
Following ADR-0001 clean architecture principles.
"""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.recurring_meeting import MeetingFrequency, RecurringMeeting
from src.domain.repositories.recurring_meeting_repository import (
    RecurringMeetingRepository,
)
from src.infrastructure.external.supabase_client import get_supabase_client


class RecurringMeetingRepositoryImpl(RecurringMeetingRepository):
    """定例MTGリポジトリのSupabase実装."""

    def __init__(self) -> None:
        """リポジトリを初期化する."""
        self._client = get_supabase_client()

    def get_by_id(self, meeting_id: UUID, user_id: UUID) -> RecurringMeeting | None:
        """IDで定例MTGを取得する."""
        if self._client is None:
            return None

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

    def get_by_google_event_id(self, google_event_id: str, user_id: UUID) -> RecurringMeeting | None:
        """Google CalendarイベントIDで定例MTGを取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("google_event_id", google_event_id)
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    def get_all(self, user_id: UUID) -> list[RecurringMeeting]:
        """ユーザーの全定例MTGを取得する."""
        if self._client is None:
            return []

        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("user_id", str(user_id))
            .order("next_occurrence", desc=False)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    def create(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを作成する."""
        if self._client is None:
            return meeting

        data = {
            "id": str(meeting.id),
            "user_id": str(meeting.user_id),
            "google_event_id": meeting.google_event_id,
            "title": meeting.title,
            "rrule": meeting.rrule,
            "frequency": meeting.frequency,
            "attendees": json.dumps(meeting.attendees),
            "next_occurrence": meeting.next_occurrence.isoformat(),
            "agent_id": str(meeting.agent_id) if meeting.agent_id else None,
            "created_at": meeting.created_at.isoformat(),
        }
        self._client.table("recurring_meetings").insert(data).execute()
        return meeting

    def update(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを更新する."""
        if self._client is None:
            return meeting

        data = {
            "title": meeting.title,
            "rrule": meeting.rrule,
            "frequency": meeting.frequency,
            "attendees": json.dumps(meeting.attendees),
            "next_occurrence": meeting.next_occurrence.isoformat(),
            "agent_id": str(meeting.agent_id) if meeting.agent_id else None,
            "updated_at": datetime.now().isoformat(),
        }
        self._client.table("recurring_meetings").update(data).eq("id", str(meeting.id)).execute()
        return meeting

    def delete(self, meeting_id: UUID, user_id: UUID) -> bool:
        """定例MTGを削除する."""
        if self._client is None:
            return False

        result = (
            self._client.table("recurring_meetings")
            .delete()
            .eq("id", str(meeting_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    def exists(self, meeting_id: UUID, user_id: UUID) -> bool:
        """定例MTGの存在を確認する."""
        if self._client is None:
            return False

        result = (
            self._client.table("recurring_meetings")
            .select("id")
            .eq("id", str(meeting_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    def get_unlinked(self, user_id: UUID) -> list[RecurringMeeting]:
        """エージェント未紐付けの定例MTGを取得する."""
        if self._client is None:
            return []

        result = (
            self._client.table("recurring_meetings")
            .select("*")
            .eq("user_id", str(user_id))
            .is_("agent_id", "null")
            .order("next_occurrence", desc=False)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    def _to_entity(self, data: dict[str, Any]) -> RecurringMeeting:
        """DB結果をエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")
        next_occurrence_str = data["next_occurrence"]

        # attendeesはJSONBなのでリストとして取得される場合とJSON文字列の場合がある
        attendees_data = data.get("attendees", [])
        if isinstance(attendees_data, str):
            attendees: list[str] = json.loads(attendees_data)
        else:
            attendees = list(attendees_data) if attendees_data else []

        # agent_idの処理
        agent_id_str = data.get("agent_id")
        agent_id: UUID | None = UUID(str(agent_id_str)) if agent_id_str else None

        # frequencyの型変換
        frequency: MeetingFrequency = data["frequency"]

        return RecurringMeeting(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            google_event_id=str(data["google_event_id"]),
            title=str(data["title"]),
            rrule=str(data["rrule"]),
            frequency=frequency,
            attendees=attendees,
            next_occurrence=(
                datetime.fromisoformat(str(next_occurrence_str))
                if isinstance(next_occurrence_str, str)
                else datetime.now()
            ),
            agent_id=agent_id,
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )
