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
    async def roles(self) -> dict[UUID, SeriesRole]:
        """Read the database's single membership definition."""

    @abstractmethod
    async def get(self, series_id: UUID) -> Series | None:
        """Read one visible series."""

    @abstractmethod
    async def attendees(self, series_id: UUID) -> tuple[Attendee, ...]:
        """Read the mirrored invite."""

    @abstractmethod
    async def occurrences(self, series_id: UUID) -> list[Occurrence]:
        """Read occurrence counts in start order."""

    @abstractmethod
    async def open_action_count(self, series_id: UUID) -> int:
        """Count unresolved actions."""

    @abstractmethod
    async def save_settings(self, access: CreatorAccess, settings: SeriesSettings, slack: SlackSource | None) -> None:
        """Write only creator-owned columns."""

    @abstractmethod
    async def delete(self, access: CreatorAccess) -> None:
        """Delete the creator's aggregate."""
