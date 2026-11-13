from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.entities.series import CreatorAccess, MemberAccess
from src.domain.entities.team_memory import ExtractedMemory, ExtractionApplyResult
from src.infrastructure.repositories.team_memory_repository_impl import TeamMemoryRepositoryImpl


def test_resolution_rpc_sends_series_boundary_without_a_pre_read() -> None:
    client = MagicMock()
    sid, item_id = uuid4(), uuid4()
    TeamMemoryRepositoryImpl(client).set_resolution(MemberAccess(sid, uuid4()), item_id, "done")
    client.table.assert_not_called()
    client.rpc.assert_called_once_with(
        "set_memory_item_resolution",
        {
            "p_series_id": str(sid),
            "p_item_id": str(item_id),
            "p_resolution": "done",
        },
    )


def test_extraction_rpc_sends_series_boundary_without_a_pre_read() -> None:
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = {"created": 0, "closed": 0}
    sid, oid, now = uuid4(), uuid4(), datetime.now(UTC)
    result = TeamMemoryRepositoryImpl(client).apply_extraction(
        CreatorAccess(sid, uuid4()), oid, ExtractedMemory((), (), False), now
    )
    assert result == ExtractionApplyResult(0, 0)
    client.table.assert_not_called()
    client.rpc.assert_called_once_with(
        "apply_extraction",
        {
            "p_series_id": str(sid),
            "p_occurrence_id": str(oid),
            "p_items": [],
            "p_closures": [],
            "p_input_at": now.isoformat(),
        },
    )
