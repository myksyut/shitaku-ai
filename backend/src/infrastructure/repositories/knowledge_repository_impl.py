from collections.abc import Sequence
from uuid import UUID

from pydantic import TypeAdapter

from src.domain.entities.knowledge import Knowledge, KnowledgeDraft
from src.domain.entities.series import CreatorAccess
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.infrastructure.external.supabase_client import UserClient


class KnowledgeRepositoryImpl(KnowledgeRepository):
    """Read and write only the explicitly selected series."""

    def __init__(self, client: UserClient) -> None:
        self._client = client

    def for_occurrences(self, series_id: UUID, occurrence_ids: Sequence[UUID]) -> list[Knowledge]:
        """Read knowledge for the given occurrences of one series."""
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
        """Read one knowledge document of the series."""
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
        """Read Drive document IDs imported into the series."""
        rows = (
            self._client.table("knowledge")
            .select("google_doc_id")
            .eq("series_id", str(series_id))
            .eq("source", "meet_transcript")
            .execute()
            .data
        )
        return frozenset(r["google_doc_id"] for r in TypeAdapter(list[dict[str, str]]).validate_python(rows))

    def add(self, access: CreatorAccess, occurrence_id: UUID, draft: KnowledgeDraft) -> Knowledge:
        """Insert knowledge, or return the already-imported Drive document."""
        if draft.google_doc_id:
            rows = (
                self._client.table("knowledge")
                .select("*")
                .eq("series_id", str(access.series_id))
                .eq("google_doc_id", draft.google_doc_id)
                .execute()
                .data
            )
            existing = TypeAdapter(list[Knowledge]).validate_python(rows)
            if existing:
                return existing[0]
        rows = (
            self._client.table("knowledge")
            .insert(
                {
                    **TypeAdapter(KnowledgeDraft).dump_python(draft, mode="json"),
                    "series_id": str(access.series_id),
                    "occurrence_id": str(occurrence_id),
                }
            )
            .execute()
            .data
        )
        return TypeAdapter(list[Knowledge]).validate_python(rows)[0]

    def delete(self, access: CreatorAccess, knowledge_id: UUID) -> None:
        """Remove only the selected series' content."""
        self._client.table("knowledge").delete().eq("series_id", str(access.series_id)).eq(
            "id", str(knowledge_id)
        ).execute()
