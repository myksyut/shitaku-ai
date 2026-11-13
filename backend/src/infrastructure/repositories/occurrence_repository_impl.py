from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter

from src.domain.entities.agenda import Agenda, AgendaTopic
from src.domain.entities.series import CreatorAccess, MemberAccess
from src.domain.repositories.occurrence_repository import OccurrenceRepository
from src.infrastructure.external.supabase_client import UserClient


class OccurrenceRepositoryImpl(OccurrenceRepository):
    """Supabase topic and agenda persistence."""

    def __init__(self, client: UserClient) -> None:
        self._client = client

    def topics(self, series_id: UUID, occurrence_id: UUID) -> list[AgendaTopic]:
        """Read posted topics in submission order."""
        rows = (
            self._client.table("agenda_topics")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("occurrence_id", str(occurrence_id))
            .order("created_at")
            .execute()
            .data
        )
        return TypeAdapter(list[AgendaTopic]).validate_python(rows)

    def topic(self, series_id: UUID, topic_id: UUID) -> AgendaTopic | None:
        """Read one topic of the series."""
        rows = (
            self._client.table("agenda_topics")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("id", str(topic_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[AgendaTopic]).validate_python(rows)
        return items[0] if items else None

    def submit_topic(self, access: MemberAccess, occurrence_id: UUID, title: str, details: str | None) -> AgendaTopic:
        """Insert the caller's topic."""
        rows = (
            self._client.table("agenda_topics")
            .insert(
                {
                    "series_id": str(access.series_id),
                    "occurrence_id": str(occurrence_id),
                    "submitted_by": str(access.user_id),
                    "title": title,
                    "details": details,
                }
            )
            .execute()
            .data
        )
        return TypeAdapter(list[AgendaTopic]).validate_python(rows)[0]

    def delete_topic(self, access: MemberAccess, topic_id: UUID) -> None:
        """Delete one topic of the series."""
        query = (
            self._client.table("agenda_topics").delete().eq("series_id", str(access.series_id)).eq("id", str(topic_id))
        )
        if not isinstance(access, CreatorAccess):
            query = query.eq("submitted_by", str(access.user_id))
        query.execute()

    def agenda(self, series_id: UUID, occurrence_id: UUID) -> Agenda | None:
        """Read the one agenda belonging to this occurrence."""
        rows = (
            self._client.table("agendas")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("occurrence_id", str(occurrence_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[Agenda]).validate_python(rows)
        return items[0] if items else None

    def save_generated(self, access: CreatorAccess, occurrence_id: UUID, content: str) -> Agenda:
        """Upsert the occurrence's generated agenda."""
        now = datetime.now(UTC)
        agenda = Agenda(occurrence_id, access.series_id, content, now, now)
        self._client.table("agendas").upsert(
            TypeAdapter(Agenda).dump_python(agenda, mode="json"), on_conflict="occurrence_id"
        ).execute()
        return agenda

    def save_edit(self, access: CreatorAccess, occurrence_id: UUID, content: str) -> Agenda | None:
        """Update an existing agenda's content."""
        rows = (
            self._client.table("agendas")
            .update({"content": content, "updated_at": datetime.now(UTC).isoformat()})
            .eq("series_id", str(access.series_id))
            .eq("occurrence_id", str(occurrence_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[Agenda]).validate_python(rows)
        return items[0] if items else None
