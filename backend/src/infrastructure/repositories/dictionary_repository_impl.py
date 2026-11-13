from uuid import UUID

from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.entities.series import CreatorAccess, SeriesError
from src.domain.repositories.dictionary_repository import DictionaryRepository


class DictionaryRepositoryImpl(DictionaryRepository):
    """Supabase vocabulary queries bounded by series ID."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def list_entries(self, series_id: UUID) -> list[DictionaryEntry]:
        """Read only this series' vocabulary."""
        rows = (
            self._client.table("dictionary_entries")
            .select("*")
            .eq("series_id", str(series_id))
            .order("canonical_name")
            .execute()
            .data
        )
        return TypeAdapter(list[DictionaryEntry]).validate_python(rows)

    def get(self, series_id: UUID, entry_id: UUID) -> DictionaryEntry | None:
        """Resolve a scoped entry ID."""
        rows = (
            self._client.table("dictionary_entries")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("id", str(entry_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[DictionaryEntry]).validate_python(rows)
        return items[0] if items else None

    def create(self, access: CreatorAccess, entry: DictionaryEntry) -> None:
        """Derive the aggregate boundary from the proof, never request data."""
        if entry.series_id != access.series_id:
            raise SeriesError(404, "Series not found")
        self._client.table("dictionary_entries").insert(
            TypeAdapter(DictionaryEntry).dump_python(entry, mode="json")
        ).execute()

    def save(self, access: CreatorAccess, entry: DictionaryEntry) -> None:
        """Write vocabulary columns only."""
        self._client.table("dictionary_entries").update(
            {
                "canonical_name": entry.canonical_name,
                "category": entry.category,
                "aliases": entry.aliases,
                "description": entry.description,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            }
        ).eq("series_id", str(access.series_id)).eq("id", str(entry.id)).execute()

    def delete(self, access: CreatorAccess, entry_id: UUID) -> None:
        """Delete the selected series' vocabulary entry."""
        self._client.table("dictionary_entries").delete().eq("series_id", str(access.series_id)).eq(
            "id", str(entry_id)
        ).execute()
