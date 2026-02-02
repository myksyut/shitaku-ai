"""DictionaryRepository implementation using Supabase."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from supabase import Client

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.repositories.dictionary_repository import DictionaryRepository


class DictionaryRepositoryImpl(DictionaryRepository):
    """Supabase implementation of DictionaryRepository."""

    def __init__(self, client: Client) -> None:
        """Initialize repository with Supabase client.

        Args:
            client: Supabase client instance.
        """
        self.client = client

    async def create(self, entry: DictionaryEntry) -> DictionaryEntry:
        """Create a new dictionary entry."""
        data: dict[str, Any] = {
            "id": str(entry.id),
            "user_id": str(entry.user_id),
            "canonical_name": entry.canonical_name,
            "description": entry.description,
            "created_at": entry.created_at.isoformat(),
            "aliases": entry.aliases,
        }
        if entry.agent_id is not None:
            data["agent_id"] = str(entry.agent_id)
        if entry.category is not None:
            data["category"] = entry.category
        self.client.table("dictionary_entries").insert(data).execute()
        return entry

    async def get_by_id(self, entry_id: UUID, user_id: UUID) -> DictionaryEntry | None:
        """Retrieve a dictionary entry by ID."""
        result = (
            self.client.table("dictionary_entries")
            .select("*")
            .eq("id", str(entry_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        return self._to_entity(cast(dict[str, Any], result.data))

    async def get_all(self, user_id: UUID) -> list[DictionaryEntry]:
        """Retrieve all dictionary entries for a user."""
        result = (
            self.client.table("dictionary_entries")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    async def update(self, entry: DictionaryEntry) -> DictionaryEntry:
        """Update an existing dictionary entry."""
        data: dict[str, Any] = {
            "canonical_name": entry.canonical_name,
            "description": entry.description,
            "updated_at": datetime.now().isoformat(),
            "aliases": entry.aliases,
        }
        if entry.agent_id is not None:
            data["agent_id"] = str(entry.agent_id)
        if entry.category is not None:
            data["category"] = entry.category
        (
            self.client.table("dictionary_entries")
            .update(data)
            .eq("id", str(entry.id))
            .eq("user_id", str(entry.user_id))
            .execute()
        )

        entry.updated_at = datetime.now()
        return entry

    async def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete a dictionary entry."""
        result = (
            self.client.table("dictionary_entries")
            .delete()
            .eq("id", str(entry_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    async def exists_by_canonical_name(
        self,
        user_id: UUID,
        canonical_name: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a canonical name already exists."""
        query = (
            self.client.table("dictionary_entries")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("canonical_name", canonical_name)
        )

        if exclude_id:
            query = query.neq("id", str(exclude_id))

        result = query.execute()
        return len(result.data) > 0

    async def find_by_agent_id(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> list[DictionaryEntry]:
        """Retrieve all dictionary entries for a specific agent."""
        result = (
            self.client.table("dictionary_entries")
            .select("*")
            .eq("agent_id", str(agent_id))
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    def _to_entity(self, data: dict[str, Any]) -> DictionaryEntry:
        """Convert database row to DictionaryEntry entity."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")

        # Handle timezone-aware ISO format
        created_at = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
        updated_at = None
        if updated_at_str:
            updated_at = datetime.fromisoformat(str(updated_at_str).replace("Z", "+00:00"))

        # Handle optional agent_id
        agent_id = None
        if data.get("agent_id"):
            agent_id = UUID(str(data["agent_id"]))

        # Handle aliases (defaults to empty list if not present)
        aliases = data.get("aliases") or []

        return DictionaryEntry(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            canonical_name=str(data["canonical_name"]),
            description=str(data["description"]) if data.get("description") else None,
            created_at=created_at,
            updated_at=updated_at,
            agent_id=agent_id,
            category=data.get("category"),
            aliases=aliases,
        )
