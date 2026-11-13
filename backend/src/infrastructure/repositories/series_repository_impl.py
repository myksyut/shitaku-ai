from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, TypeAdapter
from supabase import Client

from src.domain.entities.series import (
    Attendee,
    CalendarErrorCode,
    CreatorAccess,
    Occurrence,
    OccurrenceSummary,
    Series,
    SeriesRole,
    SeriesSettings,
    SeriesSummary,
    SlackSource,
)
from src.domain.repositories.series_repository import SeriesRepository


class _SeriesSummaryRow(BaseModel):
    id: UUID
    title: str
    created_by: UUID
    calendar_sync_error: CalendarErrorCode | None
    next_occurrence: OccurrenceSummary | None
    open_action_items: int


class SeriesRepositoryImpl(SeriesRepository):
    """Supabase series queries with explicit aggregate predicates."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def role_of_caller(self, series_id: UUID) -> SeriesRole | None:
        """Read only the requested series' role under the caller's JWT."""
        rows = self._client.rpc("my_series_roles").eq("series_id", str(series_id)).execute().data
        parsed = TypeAdapter(list[dict[str, str]]).validate_python(rows)
        return TypeAdapter[SeriesRole](SeriesRole).validate_python(parsed[0]["role"]) if parsed else None

    def list_summaries(self, user_id: UUID) -> list[SeriesSummary]:
        """Let the invoker-security view aggregate visible series in one statement."""
        rows = self._client.table("series_summary").select("*").order("title").execute().data
        summaries = TypeAdapter(list[_SeriesSummaryRow]).validate_python(rows)
        return [
            SeriesSummary(
                r.id,
                r.title,
                "creator" if r.created_by == user_id else "member",
                r.next_occurrence,
                r.open_action_items,
                r.calendar_sync_error,
            )
            for r in summaries
        ]

    def visible_calendar_series(self) -> dict[str, UUID]:
        """Expose no mapping for series hidden by the caller's RLS."""
        rows = self._client.table("series").select("id,ical_uid").execute().data
        return {r["ical_uid"]: UUID(r["id"]) for r in TypeAdapter(list[dict[str, str]]).validate_python(rows)}

    def get(self, series_id: UUID) -> Series | None:
        """Read a visible aggregate root."""
        rows = self._client.table("series").select("*").eq("id", str(series_id)).execute().data
        parsed = TypeAdapter(list[Series]).validate_python(rows)
        return parsed[0] if parsed else None

    def attendees(self, series_id: UUID) -> tuple[Attendee, ...]:
        """Read members' public calendar labels."""
        rows = (
            self._client.table("series_attendees")
            .select("*")
            .eq("series_id", str(series_id))
            .order("email")
            .execute()
            .data
        )
        return TypeAdapter(tuple[Attendee, ...]).validate_python(rows)

    def occurrences(self, series_id: UUID) -> list[Occurrence]:
        """Read the invoker-security overview."""
        rows = (
            self._client.table("occurrence_overview")
            .select("*")
            .eq("series_id", str(series_id))
            .order("start_at")
            .execute()
            .data
        )
        return TypeAdapter(list[Occurrence]).validate_python(rows)

    def get_occurrence(self, series_id: UUID, occurrence_id: UUID) -> Occurrence | None:
        """Resolve one occurrence without loading the series history."""
        rows = (
            self._client.table("occurrence_overview")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("id", str(occurrence_id))
            .execute()
            .data
        )
        parsed = TypeAdapter(list[Occurrence]).validate_python(rows)
        return parsed[0] if parsed else None

    def save_settings(
        self,
        access: CreatorAccess,
        settings: SeriesSettings,
        slack: SlackSource | None,
        google_integration_id: UUID | None,
    ) -> None:
        """Limit updates to the creator's settings columns."""
        self._client.table("series").update(
            {
                "description": settings.description,
                "minutes_count": settings.minutes_count,
                "slack_message_days": settings.slack_message_days,
                "google_integration_id": str(google_integration_id) if google_integration_id else None,
                "slack_integration_id": str(slack.integration_id) if slack else None,
                "slack_channels": [{"id": c.id, "name": c.name} for c in slack.channels] if slack else [],
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(access.series_id)).eq("created_by", str(access.user_id)).execute()

    def delete(self, access: CreatorAccess) -> None:
        """Remove only the checked creator's series."""
        self._client.table("series").delete().eq("id", str(access.series_id)).eq(
            "created_by", str(access.user_id)
        ).execute()
