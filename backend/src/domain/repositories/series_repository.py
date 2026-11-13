from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.series import (
    Attendee,
    CreatorAccess,
    Occurrence,
    Series,
    SeriesRole,
    SeriesSettings,
    SlackSource,
)


class SeriesRepository(ABC):
    """Caller-scoped series persistence."""

    @abstractmethod
    def roles(self) -> dict[UUID, SeriesRole]:
        """Read the database's single membership definition."""

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
    def open_action_count(self, series_id: UUID) -> int:
        """Count unresolved actions."""

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
