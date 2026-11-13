from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.agenda import Agenda, AgendaTopic
from src.domain.entities.series import CreatorAccess, MemberAccess


class OccurrenceRepository(ABC):
    """Topics and the occurrence's single agenda."""

    @abstractmethod
    async def topics(self, series_id: UUID, occurrence_id: UUID) -> list[AgendaTopic]:
        """Read an occurrence's posted topics."""

    @abstractmethod
    async def topic(self, series_id: UUID, topic_id: UUID) -> AgendaTopic | None:
        """Read a topic under its series boundary."""

    @abstractmethod
    async def submit_topic(
        self, access: MemberAccess, occurrence_id: UUID, title: str, details: str | None
    ) -> AgendaTopic:
        """Derive topic authorship from authenticated access."""

    @abstractmethod
    async def delete_topic(self, access: MemberAccess, topic_id: UUID) -> None:
        """Restrict deletion to authors and creators."""

    @abstractmethod
    async def agenda(self, series_id: UUID, occurrence_id: UUID) -> Agenda | None:
        """Read a scoped agenda."""

    @abstractmethod
    async def save_generated(self, access: CreatorAccess, occurrence_id: UUID, content: str) -> Agenda:
        """Replace the occurrence's generated agenda."""

    @abstractmethod
    async def save_edit(self, access: CreatorAccess, occurrence_id: UUID, content: str) -> Agenda | None:
        """Edit an existing agenda without changing its generation time."""
