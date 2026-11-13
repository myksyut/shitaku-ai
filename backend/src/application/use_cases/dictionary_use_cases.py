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

    def list_entries(self, access: MemberAccess) -> list[DictionaryEntry]:
        """Read only the checked series' entries."""
        return self.repository.list_entries(access.series_id)

    def create(
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
        self.repository.create(access, entry)
        return entry

    def update(self, access: CreatorAccess, entry_id: UUID, changes: DictionaryChanges) -> DictionaryEntry:
        """Preserve absent fields while allowing explicit nullable-field clearing."""
        entry = self.repository.get(access.series_id, entry_id)
        if entry is None:
            raise SeriesError(404, "Dictionary entry not found")
        updated = replace(entry, **changes, updated_at=datetime.now(UTC))
        self.repository.save(access, updated)
        return updated

    def delete(self, access: CreatorAccess, entry_id: UUID) -> None:
        """Reject foreign entry IDs before deleting."""
        if self.repository.get(access.series_id, entry_id) is None:
            raise SeriesError(404, "Dictionary entry not found")
        self.repository.delete(access, entry_id)
