from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NewType
from uuid import UUID

SeriesId = NewType("SeriesId", UUID)
OccurrenceId = NewType("OccurrenceId", UUID)
SeriesRole = Literal["creator", "member"]
CalendarErrorCode = Literal[
    "not_connected", "scope_missing", "revoked", "attendees_omitted", "event_not_found", "calendar_unavailable"
]
SlackErrorCode = Literal["not_connected", "not_in_channel", "rate_limited", "slack_unavailable"]


def parse_email(value: object) -> str | None:
    """Normalize a calendar or identity address."""
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    local, separator, domain = email.partition("@")
    return email if separator and local and domain and not any(c.isspace() for c in email) else None


@dataclass(frozen=True, slots=True)
class MemberAccess:
    """Proof that the caller is a series member."""

    series_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreatorAccess(MemberAccess):
    """Proof that the caller created the series."""


@dataclass(frozen=True, slots=True)
class Attendee:
    """A person on the creator's calendar invite."""

    email: str
    display_name: str | None = None
    is_organizer: bool = False


@dataclass(frozen=True, slots=True)
class OccurrenceSlot:
    """Stable original slot and its current calendar time."""

    original_start: datetime
    start_at: datetime
    is_cancelled: bool = False


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
    """A complete read from one calendar."""

    ical_uid: str
    event_id: str
    title: str
    rrule: str | None
    attendees: tuple[Attendee, ...]
    attendees_omitted: bool
    occurrences: tuple[OccurrenceSlot, ...]
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True, slots=True)
class SlackChannelRef:
    """A selected Slack channel."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class SlackSource:
    """An explicitly bound Slack integration."""

    integration_id: UUID
    channels: tuple[SlackChannelRef, ...]


@dataclass(frozen=True, slots=True)
class SeriesSettings:
    """Creator-owned settings."""

    description: str | None
    minutes_count: int
    slack_message_days: int


@dataclass(frozen=True, slots=True)
class Series:
    """A calendar-owned series with creator-owned settings."""

    id: UUID
    ical_uid: str
    created_by: UUID
    creator_event_id: str
    google_integration_id: UUID | None
    title: str
    rrule: str | None
    description: str | None
    minutes_count: int
    slack_message_days: int
    slack_integration_id: UUID | None
    slack_channels: tuple[SlackChannelRef, ...]
    calendar_synced_at: datetime
    calendar_sync_error: CalendarErrorCode | None
    calendar_refresh_attempted_at: datetime | None = None

    @property
    def slack(self) -> SlackSource | None:
        """The bound Slack source, if any."""
        return SlackSource(self.slack_integration_id, self.slack_channels) if self.slack_integration_id else None


@dataclass(frozen=True, slots=True)
class Occurrence:
    """A mirrored meeting and its derived content counts."""

    id: UUID
    series_id: UUID
    original_start: datetime
    start_at: datetime
    is_cancelled: bool
    extracted_at: datetime | None
    knowledge_count: int
    latest_knowledge_at: datetime | None
    topic_count: int
    has_agenda: bool

    @property
    def needs_extraction(self) -> bool:
        """Detect minutes not included in the last extraction."""
        return self.latest_knowledge_at is not None and (
            self.extracted_at is None or self.latest_knowledge_at > self.extracted_at
        )


@dataclass(frozen=True, slots=True)
class OccurrenceSummary:
    """Public occurrence read model."""

    id: UUID
    start_at: datetime
    is_cancelled: bool
    has_agenda: bool
    knowledge_count: int
    topic_count: int
    needs_extraction: bool

    @classmethod
    def of(cls, occurrence: Occurrence) -> "OccurrenceSummary":
        """Summarize an occurrence."""
        return cls(
            occurrence.id,
            occurrence.start_at,
            occurrence.is_cancelled,
            occurrence.has_agenda,
            occurrence.knowledge_count,
            occurrence.topic_count,
            occurrence.needs_extraction,
        )


@dataclass(frozen=True, slots=True)
class CalendarStatus:
    """Public synchronization status."""

    synced_at: datetime
    error: CalendarErrorCode | None
    google_connected: bool
    integration_id: UUID | None


@dataclass(frozen=True, slots=True)
class SeriesDetail:
    """A series as shown to its members."""

    id: UUID
    title: str
    role: SeriesRole
    rrule: str | None
    attendees: tuple[Attendee, ...]
    occurrences: tuple[OccurrenceSummary, ...]
    settings: SeriesSettings
    slack: SlackSource | None
    calendar: CalendarStatus


@dataclass(frozen=True, slots=True)
class SeriesSummary:
    """A visible series and its next meeting."""

    id: UUID
    title: str
    role: SeriesRole
    next_occurrence: OccurrenceSummary | None
    open_action_items: int
    calendar_sync_error: CalendarErrorCode | None


@dataclass(frozen=True, slots=True)
class CalendarEventChoice:
    """A live event offered by the calendar picker."""

    calendar_event_id: str
    title: str
    rrule: str | None
    attendee_count: int
    series_id: UUID | None


class SeriesError(Exception):
    """An expected series operation failure."""

    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CalendarClaim:
    """The claimed series identity, whether newly created or already present."""

    series_id: UUID
    created: bool
