from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.series import CalendarErrorCode, CalendarSnapshot, Series, SeriesError
from src.infrastructure.external.series_credentials import CredentialUnavailableError, SeriesCredentials
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.google_integration_repository_impl import GoogleIntegrationRepositoryImpl
from src.infrastructure.repositories.slack_integration_repository_impl import SlackIntegrationRepositoryImpl

_HTTP_ERROR_CODES: dict[int, CalendarErrorCode] = {
    401: "revoked",
    403: "scope_missing",
    404: "event_not_found",
    410: "event_not_found",
}


class SeriesCalendarMirror:
    """The sole privileged writer of calendar-owned series state."""

    def __init__(self, client: Client, credentials: SeriesCredentials) -> None:
        self._client = client
        self._credentials = credentials

    @classmethod
    def create(cls) -> "SeriesCalendarMirror":
        """Construct the restricted service-role boundary."""
        client = get_supabase_client()
        if client is None:
            raise SeriesError(503, "Calendar mirror is not configured")
        return cls(
            client, SeriesCredentials(GoogleIntegrationRepositoryImpl(client), SlackIntegrationRepositoryImpl(client))
        )

    async def claim(
        self, snapshot: CalendarSnapshot, creator_id: UUID, integration_id: UUID, fetched_at: datetime
    ) -> UUID | None:
        """Atomically claim an unowned iCalUID and mirror its first snapshot."""
        rows = (
            self._client.rpc(
                "claim_series",
                {
                    "p_creator_id": str(creator_id),
                    "p_integration_id": str(integration_id),
                    "p_snapshot": TypeAdapter(CalendarSnapshot).dump_python(snapshot, mode="json"),
                    "p_fetched_at": fetched_at.isoformat(),
                },
            )
            .execute()
            .data
        )
        parsed = TypeAdapter(list[dict[str, str | bool]]).validate_python(rows)
        return UUID(str(parsed[0]["series_id"])) if parsed and parsed[0]["created"] is True else None

    async def apply(self, series_id: UUID, snapshot: CalendarSnapshot, fetched_at: datetime) -> None:
        """Apply only snapshots newer than the database's last successful read."""
        self._client.rpc(
            "apply_calendar_snapshot",
            {
                "p_series_id": str(series_id),
                "p_snapshot": TypeAdapter(CalendarSnapshot).dump_python(snapshot, mode="json"),
                "p_fetched_at": fetched_at.isoformat(),
            },
        ).execute()

    async def refresh(self, series: Series) -> CalendarErrorCode | None:
        """Refresh the creator's calendar without deleting retained content on failure."""
        fetched_at = datetime.now(UTC)
        try:
            apis = await self._credentials.google_for_series(series, "calendar")
            snapshot = await apis.calendar.snapshot(series.creator_event_id, fetched_at)
            if snapshot is None or snapshot.ical_uid != series.ical_uid:
                error_code: CalendarErrorCode = "event_not_found"
            else:
                await self.apply(series.id, snapshot, fetched_at)
                return "attendees_omitted" if snapshot.attendees_omitted else None
        except CredentialUnavailableError as error:
            error_code = error.code
        except httpx.HTTPStatusError as error:
            error_code = _HTTP_ERROR_CODES.get(error.response.status_code, "calendar_unavailable")
        except (SeriesError, ValueError, httpx.HTTPError):
            error_code = "calendar_unavailable"
        self._client.table("series").update({"calendar_sync_error": error_code}).eq("id", str(series.id)).execute()
        return error_code

    async def refresh_for_join(self, ical_uid: str) -> None:
        """Re-read the trusted invite; reveal no series data to the caller."""
        rows = self._client.table("series").select("*").eq("ical_uid", ical_uid).execute().data
        series_list = TypeAdapter(list[Series]).validate_python(rows)
        if not series_list:
            return
        series = series_list[0]
        if datetime.now(UTC) - series.calendar_synced_at < timedelta(minutes=2):
            return
        if await self.refresh(series):
            raise SeriesError(409, "calendar_unavailable")
