from collections.abc import Sequence
from uuid import UUID

from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import CreatorAccess, SeriesError
from src.domain.repositories.knowledge_repository import KnowledgeRepository


class KnowledgeRepositoryImpl(KnowledgeRepository):
    """Read and write only the explicitly selected series."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def for_occurrences(self, series_id: UUID, occurrence_ids: Sequence[UUID]) -> list[Knowledge]:
        """Keep agenda and extraction sources inside their aggregate."""
        if not occurrence_ids:
            return []
        rows = (
            self._client.table("knowledge")
            .select("*")
            .eq("series_id", str(series_id))
            .in_("occurrence_id", [str(i) for i in occurrence_ids])
            .order("created_at", desc=True)
            .execute()
            .data
        )
        return TypeAdapter(list[Knowledge]).validate_python(rows)

    def get(self, series_id: UUID, knowledge_id: UUID) -> Knowledge | None:
        """Never resolve a document ID outside the access proof."""
        rows = (
            self._client.table("knowledge")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("id", str(knowledge_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[Knowledge]).validate_python(rows)
        return items[0] if items else None

    def imported_doc_ids(self, series_id: UUID) -> frozenset[str]:
        """Read shared Drive identities, not other series' documents."""
        rows = (
            self._client.table("knowledge")
            .select("google_doc_id")
            .eq("series_id", str(series_id))
            .eq("source", "meet_transcript")
            .execute()
            .data
        )
        return frozenset(r["google_doc_id"] for r in TypeAdapter(list[dict[str, str]]).validate_python(rows))

    def add(self, access: CreatorAccess, knowledge: Knowledge) -> Knowledge:
        """Persist creator-selected content and retain idempotent imports."""
        if knowledge.series_id != access.series_id:
            raise SeriesError(404, "Occurrence not found")
        if knowledge.google_doc_id:
            rows = (
                self._client.table("knowledge")
                .select("*")
                .eq("series_id", str(access.series_id))
                .eq("google_doc_id", knowledge.google_doc_id)
                .execute()
                .data
            )
            existing = TypeAdapter(list[Knowledge]).validate_python(rows)
            if existing:
                return existing[0]
        self._client.table("knowledge").insert(TypeAdapter(Knowledge).dump_python(knowledge, mode="json")).execute()
        return knowledge

    def delete(self, access: CreatorAccess, knowledge_id: UUID) -> None:
        """Remove only the selected series' content."""
        self._client.table("knowledge").delete().eq("series_id", str(access.series_id)).eq(
            "id", str(knowledge_id)
        ).execute()
