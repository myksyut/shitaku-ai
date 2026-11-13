from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from postgrest.types import CountMethod
from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.series import (
    Attendee,
    CreatorAccess,
    Occurrence,
    Series,
    SeriesRole,
    SeriesSettings,
    SlackSource,
)
from src.domain.repositories.series_repository import SeriesRepository


class SeriesRepositoryImpl(SeriesRepository):
    """Supabase series queries with explicit aggregate predicates."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def roles(self) -> dict[UUID, SeriesRole]:
        """Read roles under the caller's JWT."""
        rows = self._client.rpc("my_series_roles").execute().data
        parsed = TypeAdapter(list[dict[str, str]]).validate_python(rows)
        return {
            UUID(r["series_id"]): TypeAdapter(Literal["creator", "member"]).validate_python(r["role"]) for r in parsed
        }

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

    def open_action_count(self, series_id: UUID) -> int:
        """Count open actions without loading their text."""
        result = (
            self._client.table("memory_items")
            .select("id", count=CountMethod.exact)
            .eq("series_id", str(series_id))
            .eq("kind", "action_item")
            .is_("closed_at", "null")
            .execute()
        )
        return result.count or 0

    def save_settings(
        self,
        access: CreatorAccess,
        settings: SeriesSettings,
        slack: SlackSource | None,
        google_integration_id: UUID | None,
    ) -> None:
        """Limit updates to the creator's settings columns."""
        (
            self._client.table("series")
            .update(
                {
                    "description": settings.description,
                    "minutes_count": settings.minutes_count,
                    "slack_message_days": settings.slack_message_days,
                    "google_integration_id": str(google_integration_id) if google_integration_id else None,
                    "slack_integration_id": str(slack.integration_id) if slack else None,
                    "slack_channels": [{"id": c.id, "name": c.name} for c in slack.channels] if slack else [],
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(access.series_id))
            .eq("created_by", str(access.user_id))
            .execute()
        )

    def delete(self, access: CreatorAccess) -> None:
        """Remove only the checked creator's series."""
        self._client.table("series").delete().eq("id", str(access.series_id)).eq(
            "created_by", str(access.user_id)
        ).execute()
