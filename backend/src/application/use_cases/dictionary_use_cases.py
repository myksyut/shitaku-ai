from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.entities.dictionary_entry import DictionaryCategory, DictionaryChanges, DictionaryEntry
from src.domain.entities.series import CreatorAccess, MemberAccess, SeriesError
from src.domain.repositories.dictionary_repository import DictionaryRepository


class DictionaryUseCases:
    """Creator-owned writes to member-visible series vocabulary."""

    def __init__(self, repository: DictionaryRepository) -> None:
        self.repository = repository

    async def list_entries(self, access: MemberAccess) -> list[DictionaryEntry]:
        """Read only the checked series' entries."""
        return await self.repository.list_entries(access.series_id)

    async def create(
        self,
        access: CreatorAccess,
        canonical_name: str,
        category: DictionaryCategory | None,
        aliases: list[str],
        description: str | None,
    ) -> DictionaryEntry:
        """Assign identity and series ownership on the server."""
        entry = DictionaryEntry(
            uuid4(),
            access.series_id,
            canonical_name,
            description,
            datetime.now(UTC),
            category=category,
            aliases=aliases,
        )
        await self.repository.create(access, entry)
        return entry

    async def update(self, access: CreatorAccess, entry_id: UUID, changes: DictionaryChanges) -> DictionaryEntry:
        """Preserve absent fields while allowing explicit nullable-field clearing."""
        entry = await self.repository.get(access.series_id, entry_id)
        if entry is None:
            raise SeriesError(404, "Dictionary entry not found")
        updated = replace(entry, **changes, updated_at=datetime.now(UTC))
        await self.repository.save(access, updated)
        return updated

    async def delete(self, access: CreatorAccess, entry_id: UUID) -> None:
        """Reject foreign entry IDs before deleting."""
        if await self.repository.get(access.series_id, entry_id) is None:
            raise SeriesError(404, "Dictionary entry not found")
        await self.repository.delete(access, entry_id)
