from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import CreatorAccess


class KnowledgeRepository(ABC):
    """Explicitly selected occurrence content."""

    @abstractmethod
    def for_occurrences(self, series_id: UUID, occurrence_ids: Sequence[UUID]) -> list[Knowledge]:
        """Read only selected occurrences inside one series."""

    @abstractmethod
    def get(self, series_id: UUID, knowledge_id: UUID) -> Knowledge | None:
        """Read one scoped knowledge document."""

    @abstractmethod
    def imported_doc_ids(self, series_id: UUID) -> frozenset[str]:
        """Exclude already shared Drive documents from live candidates."""

    @abstractmethod
    def add(self, access: CreatorAccess, knowledge: Knowledge) -> Knowledge:
        """Persist selected content under the creator's proof."""

    @abstractmethod
    def delete(self, access: CreatorAccess, knowledge_id: UUID) -> None:
        """Remove a scoped shared document."""
