from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.series import (
    Attendee,
    CreatorAccess,
    Occurrence,
    Series,
    SeriesRole,
    SeriesSettings,
    SeriesSummary,
    SlackSource,
)


class SeriesRepository(ABC):
    """Caller-scoped series persistence."""

    @abstractmethod
    def role_of_caller(self, series_id: UUID) -> SeriesRole | None:
        """Read the database membership proof for one series."""

    @abstractmethod
    def list_summaries(self, user_id: UUID) -> list[SeriesSummary]:
        """Read visible series summaries with next occurrence and open action counts."""

    @abstractmethod
    def visible_calendar_series(self) -> dict[str, UUID]:
        """Map visible iCalUIDs to series IDs."""

    @abstractmethod
    def get(self, series_id: UUID) -> Series | None:
        """Read one visible series."""

    @abstractmethod
    def attendees(self, series_id: UUID) -> tuple[Attendee, ...]:
        """Read the mirrored invite."""

    @abstractmethod
    def occurrences(self, series_id: UUID) -> list[Occurrence]:
        """Read occurrence counts in start order."""

    @abstractmethod
    def get_occurrence(self, series_id: UUID, occurrence_id: UUID) -> Occurrence | None:
        """Read one occurrence of the series."""

    @abstractmethod
    def save_settings(
        self,
        access: CreatorAccess,
        settings: SeriesSettings,
        slack: SlackSource | None,
        google_integration_id: UUID | None,
    ) -> None:
        """Write only creator-owned columns."""

    @abstractmethod
    def delete(self, access: CreatorAccess) -> None:
        """Delete the creator's aggregate."""
