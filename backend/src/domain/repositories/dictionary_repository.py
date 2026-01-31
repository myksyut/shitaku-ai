"""DictionaryRepository interface for domain layer.

Abstract base class defining the contract for dictionary persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.dictionary_entry import DictionaryEntry


class DictionaryRepository(ABC):
    """Abstract repository interface for DictionaryEntry entity.

    This interface follows the Repository pattern from DDD,
    defining the contract for dictionary persistence operations.
    Concrete implementations are provided in the infrastructure layer.
    """

    @abstractmethod
    async def create(self, entry: DictionaryEntry) -> DictionaryEntry:
        """Create a new dictionary entry.

        Args:
            entry: The DictionaryEntry entity to create.

        Returns:
            The created DictionaryEntry entity.
        """

    @abstractmethod
    async def get_by_id(self, entry_id: UUID, user_id: UUID) -> DictionaryEntry | None:
        """Retrieve a dictionary entry by ID.

        Args:
            entry_id: The unique identifier of the entry.
            user_id: The user ID for RLS filtering.

        Returns:
            The DictionaryEntry if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, user_id: UUID) -> list[DictionaryEntry]:
        """Retrieve all dictionary entries for a user.

        Args:
            user_id: The user ID.

        Returns:
            A list of DictionaryEntry entities.
        """

    @abstractmethod
    async def update(self, entry: DictionaryEntry) -> DictionaryEntry:
        """Update an existing dictionary entry.

        Args:
            entry: The DictionaryEntry entity with updated values.

        Returns:
            The updated DictionaryEntry entity.
        """

    @abstractmethod
    async def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete a dictionary entry.

        Args:
            entry_id: The unique identifier of the entry.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    async def exists_by_canonical_name(
        self,
        user_id: UUID,
        canonical_name: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a canonical name already exists.

        Args:
            user_id: The user ID.
            canonical_name: The canonical name to check.
            exclude_id: Entry ID to exclude (for update checks).

        Returns:
            True if duplicate exists.
        """
