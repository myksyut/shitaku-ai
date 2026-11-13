from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.entities.series import CreatorAccess


class DictionaryRepository(ABC):
    """Vocabulary shared only within the access proof's series."""

    @abstractmethod
    async def list_entries(self, series_id: UUID) -> list[DictionaryEntry]:
        """Read the series vocabulary."""

    @abstractmethod
    async def get(self, series_id: UUID, entry_id: UUID) -> DictionaryEntry | None:
        """Read a scoped entry."""

    @abstractmethod
    async def create(self, access: CreatorAccess, entry: DictionaryEntry) -> None:
        """Create a creator-owned vocabulary entry."""

    @abstractmethod
    async def save(self, access: CreatorAccess, entry: DictionaryEntry) -> None:
        """Update an existing aggregate-scoped entry."""

    @abstractmethod
    async def delete(self, access: CreatorAccess, entry_id: UUID) -> None:
        """Delete one aggregate-scoped entry."""
