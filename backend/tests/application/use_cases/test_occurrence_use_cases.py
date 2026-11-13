from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.occurrence_use_cases import OccurrenceUseCases
from src.domain.entities.series import CreatorAccess, MemberAccess, Occurrence, SeriesError
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.repositories.occurrence_repository import OccurrenceRepository
from src.domain.repositories.series_repository import SeriesRepository
from src.domain.services.normalization_service import NormalizationService
from src.infrastructure.external.google_docs_client import DocsDocument
from src.infrastructure.external.google_drive_client import GOOGLE_DOCS_MIME_TYPE, DriveFile
from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials
from tests.application.use_cases.test_series_use_cases import make_series


def occurrence(sid: UUID, *, cancelled: bool = False, days: int = 1) -> Occurrence:
    start = datetime.now(UTC) + timedelta(days=days)
    return Occurrence(uuid4(), sid, start, start, cancelled, None, 0, None, 0, False)


def make_use_cases() -> tuple[OccurrenceUseCases, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    series = AsyncMock(spec=SeriesRepository)
    content = AsyncMock(spec=OccurrenceRepository)
    knowledge = AsyncMock(spec=KnowledgeRepository)
    credentials = AsyncMock(spec=SeriesCredentials)
    use_cases = OccurrenceUseCases(
        series,
        content,
        knowledge,
        AsyncMock(spec=DictionaryRepository),
        credentials,
        MagicMock(spec=NormalizationService),
    )
    return use_cases, series, content, knowledge, credentials


@pytest.mark.parametrize(("cancelled", "days"), [(True, 1), (False, -1)])
async def test_topics_reject_cancelled_or_started_occurrences(cancelled: bool, days: int) -> None:
    use_cases, series, content, _, _ = make_use_cases()
    sid = uuid4()
    target = occurrence(sid, cancelled=cancelled, days=days)
    series.occurrences.return_value = [target]
    with pytest.raises(SeriesError) as error:
        await use_cases.submit_topic(MemberAccess(sid, uuid4()), target.id, "Topic", None)
    assert error.value.status == 422
    content.submit_topic.assert_not_called()


async def test_drive_candidates_are_live_creator_scoped_and_windowed() -> None:
    use_cases, series, _, knowledge, credentials = make_use_cases()
    sid, owner = uuid4(), uuid4()
    target = occurrence(sid)
    series.occurrences.return_value = [target]
    series.get.return_value = make_series(sid, owner)
    lower, upper = target.start_at - timedelta(hours=1), target.start_at + timedelta(hours=24)
    files = [
        DriveFile(name, name, GOOGLE_DOCS_MIME_TYPE, created, created, None)
        for name, created in (("lower", lower), ("upper", upper), ("outside", upper + timedelta(seconds=1)))
    ]
    drive, docs = AsyncMock(), AsyncMock()
    apis = GoogleApis(MagicMock(), drive, docs)
    drive.search_transcript_files.return_value = files
    credentials.google_for_series.return_value = apis
    knowledge.imported_doc_ids.return_value = frozenset({"upper"})
    candidates = await use_cases.transcript_candidates(CreatorAccess(sid, owner), target.id)
    assert [c.google_doc_id for c in candidates] == ["lower"]
    drive.search_transcript_files.assert_awaited_once_with(created_after=lower, created_before=upper)
    credentials.google_for_series.assert_awaited_once_with(series.get.return_value, "drive")
    knowledge.add.assert_not_called()
    docs.get_document_content.return_value = DocsDocument("lower", "Picked", "Shared transcript")
    knowledge.add.side_effect = lambda access, document: document
    result = await use_cases.add_transcript(CreatorAccess(sid, owner), target.id, "lower")
    assert result.knowledge.google_doc_id == "lower"
    assert result.knowledge.series_id == sid
    assert result.knowledge.normalized_text == "Shared transcript"
    docs.get_document_content.assert_awaited_once_with("lower")
    with pytest.raises(SeriesError) as error:
        await use_cases.add_transcript(CreatorAccess(sid, owner), target.id, "outside")
    assert error.value.status == 404
    assert docs.get_document_content.await_count == 1
