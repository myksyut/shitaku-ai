import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from src.domain.entities.agenda import Agenda, AgendaTopic
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import CreatorAccess, MemberAccess, Occurrence, SeriesError
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.repositories.occurrence_repository import OccurrenceRepository
from src.domain.repositories.series_repository import SeriesRepository
from src.domain.services.normalization_service import NormalizationError, NormalizationService
from src.infrastructure.external.google_drive_client import GOOGLE_DOCS_MIME_TYPE, DriveFile
from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials


@dataclass(frozen=True, slots=True)
class OccurrenceContent:
    """The occurrence's shared content before public-field projection."""

    occurrence: Occurrence
    agenda: Agenda | None
    topics: list[AgendaTopic]
    knowledge: list[Knowledge]


@dataclass(frozen=True, slots=True)
class TranscriptCandidate:
    """A live, unpersisted Drive document choice."""

    google_doc_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AddKnowledgeResult:
    """Saved content plus visible normalization outcome."""

    knowledge: Knowledge
    normalization_warning: str | None
    replacement_count: int


class OccurrenceUseCases:
    """Shared topics and explicitly selected occurrence knowledge."""

    def __init__(
        self,
        series: SeriesRepository,
        content: OccurrenceRepository,
        knowledge: KnowledgeRepository,
        dictionary: DictionaryRepository,
        credentials: SeriesCredentials,
        normalizer: NormalizationService,
    ) -> None:
        self.series, self.content, self.knowledge = series, content, knowledge
        self.dictionary, self.credentials, self.normalizer = dictionary, credentials, normalizer

    async def occurrence(self, access: MemberAccess, occurrence_id: UUID) -> Occurrence:
        """Resolve IDs only through the checked series aggregate."""
        occurrence = next((o for o in await self.series.occurrences(access.series_id) if o.id == occurrence_id), None)
        if occurrence is None:
            raise SeriesError(404, "Occurrence not found")
        return occurrence

    async def detail(self, access: MemberAccess, occurrence_id: UUID) -> OccurrenceContent:
        """Read agenda, topics and selected documents for one occurrence."""
        return OccurrenceContent(
            await self.occurrence(access, occurrence_id),
            await self.content.agenda(access.series_id, occurrence_id),
            await self.content.topics(access.series_id, occurrence_id),
            await self.knowledge.for_occurrences(access.series_id, [occurrence_id]),
        )

    async def submit_topic(
        self, access: MemberAccess, occurrence_id: UUID, title: str, details: str | None
    ) -> AgendaTopic:
        """Reject started and cancelled meetings before the RLS recheck."""
        occurrence = await self.occurrence(access, occurrence_id)
        if occurrence.is_cancelled or occurrence.start_at <= datetime.now(UTC):
            raise SeriesError(422, "Topics require a future noncancelled occurrence")
        return await self.content.submit_topic(access, occurrence_id, title, details)

    async def delete_topic(self, access: MemberAccess, topic_id: UUID) -> None:
        """Only the author or series creator can withdraw a suggestion."""
        topic = await self.content.topic(access.series_id, topic_id)
        if topic is None:
            raise SeriesError(404, "Topic not found")
        if not isinstance(access, CreatorAccess) and topic.submitted_by != access.user_id:
            raise SeriesError(403, "Only the author or creator can delete this topic")
        await self.content.delete_topic(access, topic_id)

    async def _drive_files(self, access: CreatorAccess, occurrence_id: UUID) -> tuple[GoogleApis, list[DriveFile]]:
        occurrence = await self.occurrence(access, occurrence_id)
        series = await self.series.get(access.series_id)
        if series is None:
            raise SeriesError(404, "Series not found")
        apis = await self.credentials.google_for_series(series, "drive")
        lower, upper = occurrence.start_at - timedelta(hours=1), occurrence.start_at + timedelta(hours=24)
        try:
            files = await apis.drive.search_transcript_files(created_after=lower, created_before=upper)
        except (ValueError, httpx.HTTPError) as error:
            raise SeriesError(502, "Transcript candidates unavailable") from error
        return apis, [f for f in files if f.mime_type == GOOGLE_DOCS_MIME_TYPE and lower <= f.created_time <= upper]

    async def transcript_candidates(self, access: CreatorAccess, occurrence_id: UUID) -> list[TranscriptCandidate]:
        """List live creator Drive candidates without storing unselected documents."""
        _, files = await self._drive_files(access, occurrence_id)
        imported = await self.knowledge.imported_doc_ids(access.series_id)
        return [TranscriptCandidate(f.id, f.name, f.created_time) for f in files if f.id not in imported]

    async def add_upload(self, access: CreatorAccess, occurrence_id: UUID, text: str) -> AddKnowledgeResult:
        """Normalize only against this series' dictionary, reporting failures."""
        await self.occurrence(access, occurrence_id)
        dictionary = await self.dictionary.list_entries(access.series_id)
        warning = None
        replacement_count = 0
        normalized = text
        try:
            result = await asyncio.to_thread(self.normalizer.normalize, text, dictionary)
            normalized, warning, replacement_count = result.normalized_text, result.warning, result.replacement_count
        except NormalizationError as error:
            warning = str(error)
        knowledge = Knowledge(
            uuid4(), access.series_id, occurrence_id, "upload", None, None, text, normalized, datetime.now(UTC)
        )
        return AddKnowledgeResult(await self.knowledge.add(access, knowledge), warning, replacement_count)

    async def add_transcript(
        self, access: CreatorAccess, occurrence_id: UUID, google_doc_id: str
    ) -> AddKnowledgeResult:
        """Import only a picked candidate from the creator's bound Drive."""
        apis, files = await self._drive_files(access, occurrence_id)
        if not any(f.id == google_doc_id for f in files):
            raise SeriesError(404, "Transcript candidate not found")
        try:
            document = await apis.docs.get_document_content(google_doc_id)
        except (ValueError, httpx.HTTPError) as error:
            raise SeriesError(502, "Transcript unavailable") from error
        if document is None:
            raise SeriesError(404, "Transcript not found")
        knowledge = Knowledge(
            uuid4(),
            access.series_id,
            occurrence_id,
            "meet_transcript",
            google_doc_id,
            document.title,
            document.body_text,
            document.body_text,
            datetime.now(UTC),
        )
        return AddKnowledgeResult(await self.knowledge.add(access, knowledge), None, 0)

    async def get_knowledge(self, access: MemberAccess, knowledge_id: UUID) -> Knowledge:
        """Read only selected shared content."""
        result = await self.knowledge.get(access.series_id, knowledge_id)
        if result is None:
            raise SeriesError(404, "Knowledge not found")
        return result

    async def delete_knowledge(self, access: CreatorAccess, knowledge_id: UUID) -> None:
        """Delete only visible aggregate-scoped knowledge."""
        await self.get_knowledge(access, knowledge_id)
        await self.knowledge.delete(access, knowledge_id)

    async def save_agenda(self, access: CreatorAccess, occurrence_id: UUID, content: str) -> Agenda:
        """Edit one existing occurrence agenda."""
        await self.occurrence(access, occurrence_id)
        result = await self.content.save_edit(access, occurrence_id, content)
        if result is None:
            raise SeriesError(404, "Agenda not found")
        return result
