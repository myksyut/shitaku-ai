import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
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

logger = logging.getLogger(__name__)


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

    def claim(
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

    def apply(self, series_id: UUID, snapshot: CalendarSnapshot, fetched_at: datetime) -> None:
        """Apply only snapshots newer than the database's last successful read."""
        self._client.rpc(
            "apply_calendar_snapshot",
            {
                "p_series_id": str(series_id),
                "p_snapshot": TypeAdapter(CalendarSnapshot).dump_python(snapshot, mode="json"),
                "p_fetched_at": fetched_at.isoformat(),
            },
        ).execute()

    def refresh(self, series: Series, *, throttle: bool = False) -> CalendarErrorCode | None:
        """Refresh the creator's calendar without deleting retained content on failure."""
        fetched_at = datetime.now(UTC)
        try:
            started = (
                self._client.rpc(
                    "begin_calendar_refresh",
                    {
                        "p_series_id": str(series.id),
                        "p_attempted_at": fetched_at.isoformat(),
                        "p_throttle": throttle,
                    },
                )
                .execute()
                .data
            )
            if not TypeAdapter(bool).validate_python(started):
                return series.calendar_sync_error
            apis = self._credentials.google_for_series(series, "calendar")
            snapshot = apis.calendar.snapshot(series.creator_event_id, fetched_at)
            if snapshot is None or snapshot.ical_uid != series.ical_uid:
                self._client.rpc(
                    "mark_calendar_event_missing",
                    {
                        "p_series_id": str(series.id),
                        "p_fetched_at": fetched_at.isoformat(),
                    },
                ).execute()
                error_code: CalendarErrorCode = "event_not_found"
            else:
                self.apply(series.id, snapshot, fetched_at)
                return "attendees_omitted" if snapshot.attendees_omitted else None
        except CredentialUnavailableError as error:
            error_code = error.code
        except httpx.HTTPStatusError as error:
            error_code = _HTTP_ERROR_CODES.get(error.response.status_code, "calendar_unavailable")
        except (SeriesError, ValueError, httpx.HTTPError, APIError):
            error_code = "calendar_unavailable"
        try:
            self._client.table("series").update({"calendar_sync_error": error_code}).eq("id", str(series.id)).execute()
        except APIError as error:
            logger.warning("Calendar error persistence failed: code=%s message=%s", error.code, error.message)
        return error_code

    def refresh_for_join(self, ical_uid: str) -> None:
        """Re-read the trusted invite; reveal no series data to the caller."""
        rows = self._client.table("series").select("*").eq("ical_uid", ical_uid).execute().data
        series_list = TypeAdapter(list[Series]).validate_python(rows)
        if not series_list:
            return
        series = series_list[0]
        if series.calendar_refresh_attempted_at is not None and datetime.now(
            UTC
        ) - series.calendar_refresh_attempted_at < timedelta(minutes=2):
            return
        error = self.refresh(series, throttle=True)
        if error not in (None, "attendees_omitted"):
            raise SeriesError(409, "calendar_unavailable")
