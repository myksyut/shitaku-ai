from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from postgrest.types import JSON
from pydantic import BaseModel, TypeAdapter
from supabase import Client

from src.domain.entities.series import CreatorAccess, MemberAccess, SeriesError
from src.domain.entities.team_memory import ExtractedMemory, ExtractionApplyResult, MemoryItem, NewMemory, Resolution
from src.domain.repositories.team_memory_repository import TeamMemoryRepository


class OriginTime(BaseModel):
    """The embedded origin occurrence's start time."""

    start_at: datetime


class MemoryRow(BaseModel):
    """A memory row's embedded origin occurrence."""

    origin: OriginTime


def extraction_key(kind: str, body: str) -> str:
    """Build the dedupe key for an extracted memory item."""
    return sha256(f"{kind}\0{' '.join(body.split())}".encode()).hexdigest()


def memory_rows(raw: object) -> list[MemoryItem]:
    """Parse memory_items rows into domain memory items."""
    rows = TypeAdapter(list[dict[str, JSON]]).validate_python(raw)
    return [
        TypeAdapter(MemoryItem).validate_python(
            {**row, "origin_start_at": MemoryRow.model_validate(row).origin.start_at}
        )
        for row in rows
    ]


class TeamMemoryRepositoryImpl(TeamMemoryRepository):
    """Supabase team memory persistence."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def list_items(self, series_id: UUID) -> list[MemoryItem]:
        """Read memory only inside the requested series."""
        rows = (
            self._client.table("memory_items")
            .select("*,origin:occurrences(start_at)")
            .eq("series_id", str(series_id))
            .order("created_at")
            .execute()
            .data
        )
        return memory_rows(rows)

    def get(self, series_id: UUID, item_id: UUID) -> MemoryItem | None:
        """Read one memory item of the series."""
        rows = (
            self._client.table("memory_items")
            .select("*,origin:occurrences(start_at)")
            .eq("series_id", str(series_id))
            .eq("id", str(item_id))
            .execute()
            .data
        )
        items = memory_rows(rows)
        return items[0] if items else None

    def add(self, access: CreatorAccess, draft: NewMemory) -> None:
        """Insert a human-authored memory item."""
        payload = TypeAdapter(dict[str, JSON]).validate_python(
            TypeAdapter[NewMemory](NewMemory).dump_python(draft, mode="json")
        )
        self._client.table("memory_items").insert(
            {
                **payload,
                "series_id": str(access.series_id),
                "extracted": False,
                "human_updated_at": datetime.now(UTC).isoformat(),
            }
        ).execute()

    def edit(self, access: CreatorAccess, item_id: UUID, draft: NewMemory) -> None:
        """Apply a human edit to a same-kind memory item."""
        payload = TypeAdapter(dict[str, JSON]).validate_python(
            TypeAdapter[NewMemory](NewMemory).dump_python(draft, mode="json")
        )
        self._client.table("memory_items").update({**payload, "human_updated_at": datetime.now(UTC).isoformat()}).eq(
            "series_id", str(access.series_id)
        ).eq("id", str(item_id)).eq("kind", draft.kind).execute()

    def set_resolution(self, access: MemberAccess, item_id: UUID, resolution: Resolution | None) -> None:
        """Set or clear an item's resolution."""
        if self.get(access.series_id, item_id) is None:
            raise SeriesError(404, "Memory item not found")
        self._client.rpc(
            "set_memory_item_resolution", {"p_item_id": str(item_id), "p_resolution": resolution}
        ).execute()

    def delete(self, access: CreatorAccess, item_id: UUID) -> None:
        """Delete only the checked series' item."""
        self._client.table("memory_items").delete().eq("series_id", str(access.series_id)).eq(
            "id", str(item_id)
        ).execute()

    def apply_extraction(
        self, access: CreatorAccess, occurrence_id: UUID, extracted: ExtractedMemory, input_at: datetime
    ) -> ExtractionApplyResult:
        """Persist extracted memory for one occurrence."""
        occurrence = (
            self._client.table("occurrences")
            .select("id")
            .eq("series_id", str(access.series_id))
            .eq("id", str(occurrence_id))
            .execute()
            .data
        )
        if not occurrence:
            raise SeriesError(404, "Occurrence not found")
        items: list[JSON] = []
        for draft in extracted.new_items:
            payload = TypeAdapter(dict[str, JSON]).validate_python(
                TypeAdapter[NewMemory](NewMemory).dump_python(draft, mode="json")
            )
            items.append({**payload, "extraction_key": extraction_key(draft.kind, draft.body)})
        result = (
            self._client.rpc(
                "apply_extraction",
                {
                    "p_occurrence_id": str(occurrence_id),
                    "p_input_at": input_at.isoformat(),
                    "p_items": items,
                    "p_closures": [{"item_id": str(c.item_id), "resolution": c.resolution} for c in extracted.closures],
                },
            )
            .execute()
            .data
        )
        return TypeAdapter(ExtractionApplyResult).validate_python(result)
