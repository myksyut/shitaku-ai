from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.entities.knowledge import KnowledgeDraft
from src.domain.entities.series import CreatorAccess
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl


def test_repository_omits_database_owned_fields_and_returns_persisted_timestamp() -> None:
    sid, oid, kid, uid = uuid4(), uuid4(), uuid4(), uuid4()
    timestamp = datetime(2026, 11, 13, tzinfo=UTC)
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": str(kid),
            "series_id": str(sid),
            "occurrence_id": str(oid),
            "source": "upload",
            "google_doc_id": None,
            "title": None,
            "original_text": "Original",
            "normalized_text": "Normalized",
            "created_at": timestamp.isoformat(),
        }
    ]
    saved = KnowledgeRepositoryImpl(client).add(
        CreatorAccess(sid, uid), oid, KnowledgeDraft("upload", None, None, "Original", "Normalized")
    )
    payload = client.table.return_value.insert.call_args.args[0]
    assert "created_at" not in payload and "id" not in payload
    assert payload["series_id"] == str(sid) and payload["occurrence_id"] == str(oid)
    assert saved.id == kid and saved.created_at == timestamp
