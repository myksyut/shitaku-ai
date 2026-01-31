"""Use cases for dictionary operations."""

from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.repositories.dictionary_repository import DictionaryRepository


class CreateDictionaryEntryUseCase:
    """Use case for creating a dictionary entry."""

    def __init__(self, repository: DictionaryRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        user_id: UUID,
        canonical_name: str,
        description: str | None,
    ) -> DictionaryEntry:
        """Create a new dictionary entry.

        Args:
            user_id: The user ID.
            canonical_name: The canonical name.
            description: Optional description.

        Returns:
            The created DictionaryEntry.

        Raises:
            ValueError: If canonical_name already exists for this user.
        """
        if await self.repository.exists_by_canonical_name(user_id, canonical_name):
            raise ValueError(f"Entry with canonical_name '{canonical_name}' already exists")

        entry = DictionaryEntry(
            id=uuid4(),
            user_id=user_id,
            canonical_name=canonical_name,
            description=description,
            created_at=datetime.now(),
            updated_at=None,
        )

        return await self.repository.create(entry)


class GetDictionaryEntriesUseCase:
    """Use case for getting all dictionary entries."""

    def __init__(self, repository: DictionaryRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, user_id: UUID) -> list[DictionaryEntry]:
        """Get all dictionary entries for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of DictionaryEntry entities.
        """
        return await self.repository.get_all(user_id)


class GetDictionaryEntryUseCase:
    """Use case for getting a single dictionary entry."""

    def __init__(self, repository: DictionaryRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, entry_id: UUID, user_id: UUID) -> DictionaryEntry | None:
        """Get a dictionary entry by ID.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.

        Returns:
            DictionaryEntry if found, None otherwise.
        """
        return await self.repository.get_by_id(entry_id, user_id)


class UpdateDictionaryEntryUseCase:
    """Use case for updating a dictionary entry."""

    def __init__(self, repository: DictionaryRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(
        self,
        entry_id: UUID,
        user_id: UUID,
        canonical_name: str | None,
        description: str | None,
    ) -> DictionaryEntry | None:
        """Update a dictionary entry.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.
            canonical_name: New canonical name (optional).
            description: New description (optional).

        Returns:
            Updated DictionaryEntry if found, None otherwise.

        Raises:
            ValueError: If canonical_name already exists for this user.
        """
        entry = await self.repository.get_by_id(entry_id, user_id)
        if not entry:
            return None

        if canonical_name and canonical_name != entry.canonical_name:
            if await self.repository.exists_by_canonical_name(user_id, canonical_name, entry_id):
                raise ValueError(f"Entry with canonical_name '{canonical_name}' already exists")
            entry.canonical_name = canonical_name

        if description is not None:
            entry.description = description

        entry.updated_at = datetime.now()
        return await self.repository.update(entry)


class DeleteDictionaryEntryUseCase:
    """Use case for deleting a dictionary entry."""

    def __init__(self, repository: DictionaryRepository) -> None:
        """Initialize use case with repository."""
        self.repository = repository

    async def execute(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete a dictionary entry.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """
        return await self.repository.delete(entry_id, user_id)
