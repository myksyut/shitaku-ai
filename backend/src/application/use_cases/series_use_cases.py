from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.domain.entities.series import (
    CalendarEventChoice,
    CalendarStatus,
    CreatorAccess,
    MemberAccess,
    OccurrenceSummary,
    SeriesDetail,
    SeriesError,
    SeriesSettings,
    SeriesSummary,
    SlackChannelRef,
    SlackSource,
)
from src.domain.repositories.series_repository import SeriesRepository
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import SeriesCredentials


class SeriesUseCases:
    """Read and configure a member-visible series."""

    def __init__(self, repository: SeriesRepository) -> None:
        self.repository = repository

    def detail(self, access: MemberAccess) -> SeriesDetail:
        """Project a series without personal integration credentials."""
        series = self.repository.get(access.series_id)
        if series is None:
            raise SeriesError(404, "Series not found")
        return SeriesDetail(
            series.id,
            series.title,
            "creator" if isinstance(access, CreatorAccess) else "member",
            series.rrule,
            self.repository.attendees(series.id),
            tuple(OccurrenceSummary.of(o) for o in self.repository.occurrences(series.id)),
            SeriesSettings(series.description, series.minutes_count, series.slack_message_days),
            series.slack,
            CalendarStatus(
                series.calendar_synced_at,
                series.calendar_sync_error,
                series.google_integration_id is not None,
                series.google_integration_id,
            ),
        )

    def list_for_caller(self, user_id: UUID) -> list[SeriesSummary]:
        """Read RLS-scoped summaries without per-series queries."""
        return self.repository.list_summaries(user_id)

    def settings(
        self,
        access: CreatorAccess,
        settings: SeriesSettings,
        credentials: SeriesCredentials,
        google_integration_id: UUID | None,
        integration_id: UUID | None,
        channel_ids: list[str],
    ) -> SeriesDetail:
        """Resolve selected channel names from the creator's own Slack."""
        if google_integration_id is not None:
            credentials.validate_calendar_integration(access.user_id, google_integration_id)
        slack = None
        if integration_id is not None:
            client = credentials.slack_for_user(access.user_id, integration_id)
            channels = {c.id: c.name for c in client.get_channels()}
            if any(cid not in channels for cid in channel_ids):
                raise SeriesError(422, "Unknown Slack channel")
            slack = SlackSource(
                integration_id, tuple(SlackChannelRef(cid, channels[cid]) for cid in dict.fromkeys(channel_ids))
            )
        self.repository.save_settings(access, settings, slack, google_integration_id)
        return self.detail(access)


class CalendarUseCases:
    """Select a live calendar event, then claim or join its shared series."""

    def __init__(
        self, repository: SeriesRepository, credentials: SeriesCredentials, mirror: SeriesCalendarMirror
    ) -> None:
        self.repository = repository
        self.credentials = credentials
        self.mirror = mirror

    def choices(self, user_id: UUID, integration_id: UUID) -> list[CalendarEventChoice]:
        """Show existing series identifiers only when the caller can read them."""
        apis = self.credentials.google_for_user(user_id, integration_id, "calendar")
        visible = self.repository.visible_calendar_series()
        return [
            CalendarEventChoice(s.event_id, s.title, s.rrule, len(s.attendees), visible.get(s.ical_uid))
            for s in apis.calendar.list_recurring_masters()
        ]

    def claim(
        self, user_id: UUID, integration_id: UUID, event_id: str, verified_emails: frozenset[str]
    ) -> tuple[str, UUID]:
        """Re-check membership with the caller's JWT after the privileged boundary."""
        fetched_at = datetime.now(UTC)
        apis = self.credentials.google_for_user(user_id, integration_id, "calendar")
        try:
            snapshot = apis.calendar.snapshot(event_id, fetched_at)
        except ValueError as error:
            raise SeriesError(422, str(error)) from error
        if snapshot is None:
            raise SeriesError(404, "Calendar event not found")
        if not snapshot.rrule or not verified_emails.intersection(a.email for a in snapshot.attendees):
            raise SeriesError(422, "You are not a verified participant of this recurring event")
        claim = self.mirror.claim(snapshot, user_id, integration_id, fetched_at)
        if claim.created:
            return "created", claim.series_id
        if self.repository.get(claim.series_id) is not None:
            return "already_member", claim.series_id
        self.mirror.refresh_for_join(snapshot.ical_uid)
        if self.repository.get(claim.series_id) is None:
            raise SeriesError(403, "You are not on the creator's calendar invite")
        return "joined", claim.series_id
