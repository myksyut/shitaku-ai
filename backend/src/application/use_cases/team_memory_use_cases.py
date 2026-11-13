from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.domain.entities.series import CreatorAccess, MemberAccess, SeriesError
from src.domain.entities.team_memory import ActionItem, Decision, MemoryItem, NewActionItem, NewMemory, Resolution
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.repositories.series_repository import SeriesRepository
from src.domain.repositories.team_memory_repository import TeamMemoryRepository
from src.domain.services.team_memory_rules import resolution_allowed, with_carry_over
from src.infrastructure.services.meeting_memory_extractor import ExtractionContext, MeetingMemoryExtractor


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Persisted extraction counts and the refreshed shared board."""

    created: int
    closed: int
    truncated: bool
    items: list[MemoryItem]


class TeamMemoryUseCases:
    """Authorize and validate every human memory mutation."""

    def __init__(self, memory: TeamMemoryRepository, series: SeriesRepository) -> None:
        self.memory = memory
        self.series = series

    def board(self, access: MemberAccess) -> list[MemoryItem]:
        """Derive carry counts against the next noncancelled meeting."""
        occurrences = self.series.occurrences(access.series_id)
        now = datetime.now(UTC)
        target = next((o.start_at for o in occurrences if not o.is_cancelled and o.start_at > now), now)
        return with_carry_over(self.memory.list_items(access.series_id), occurrences, target, now)

    def _validate_draft(self, access: CreatorAccess, draft: NewMemory) -> None:
        if self.series.get_occurrence(access.series_id, draft.origin_occurrence_id) is None:
            raise SeriesError(404, "Occurrence not found")
        if (
            isinstance(draft, NewActionItem)
            and draft.assignee_email is not None
            and draft.assignee_email not in {a.email for a in self.series.attendees(access.series_id)}
        ):
            raise SeriesError(422, "Assignee must be a series attendee")

    def _item(self, access: MemberAccess, item_id: UUID) -> MemoryItem:
        item = self.memory.get(access.series_id, item_id)
        if item is None:
            raise SeriesError(404, "Memory item not found")
        return item

    def add(self, access: CreatorAccess, draft: NewMemory) -> list[MemoryItem]:
        """Create only valid aggregate-scoped memory."""
        self._validate_draft(access, draft)
        self.memory.add(access, draft)
        return self.board(access)

    def edit(self, access: CreatorAccess, item_id: UUID, draft: NewMemory) -> list[MemoryItem]:
        """Editing cannot change an item's kind."""
        item = self._item(access, item_id)
        if item.kind != draft.kind:
            raise SeriesError(422, "Memory kind cannot change")
        self._validate_draft(access, draft)
        self.memory.edit(access, item_id, draft)
        return self.board(access)

    def resolve(self, access: MemberAccess, item_id: UUID, resolution: Resolution | None) -> list[MemoryItem]:
        """Members may resolve actions; only creators may change other kinds."""
        item = self._item(access, item_id)
        if not isinstance(access, CreatorAccess) and not isinstance(item, ActionItem):
            raise SeriesError(403, "Only the creator can change this item")
        if not resolution_allowed(item, resolution, creator=isinstance(access, CreatorAccess)):
            raise SeriesError(422, "Resolution does not fit memory kind")
        self.memory.set_resolution(access, item_id, resolution)
        return self.board(access)

    def delete(self, access: CreatorAccess, item_id: UUID) -> list[MemoryItem]:
        """Delete a visible item and return the updated board."""
        self._item(access, item_id)
        self.memory.delete(access, item_id)
        return self.board(access)


class ExtractOccurrenceMemory:
    """Read a bounded input snapshot, extract once, apply atomically."""

    def __init__(
        self,
        memory: TeamMemoryRepository,
        series: SeriesRepository,
        knowledge: KnowledgeRepository,
        dictionary: DictionaryRepository,
        extractor: MeetingMemoryExtractor,
    ) -> None:
        self.memory, self.series = memory, series
        self.knowledge, self.dictionary, self.extractor = knowledge, dictionary, extractor

    def execute(self, access: CreatorAccess, occurrence_id: UUID) -> ExtractionResult:
        """Timestamp the input before reading so concurrent minutes remain unextracted."""
        input_at = datetime.now(UTC)
        occurrence = self.series.get_occurrence(access.series_id, occurrence_id)
        if occurrence is None:
            raise SeriesError(404, "Occurrence not found")
        if occurrence.start_at > input_at:
            raise SeriesError(422, "Meeting has not started")
        series = self.series.get(access.series_id)
        if series is None:
            raise SeriesError(404, "Series not found")
        sources = self.knowledge.for_occurrences(access.series_id, [occurrence_id])
        if not sources:
            raise SeriesError(422, "Add meeting notes before extracting")
        items = self.memory.list_items(access.series_id)
        eligible = [
            i
            for i in items
            if i.closed_at is None
            and i.origin_start_at <= occurrence.start_at
            and not (i.origin_occurrence_id == occurrence_id and i.extracted and i.human_updated_at is None)
        ]
        open_work = [i for i in eligible if not isinstance(i, Decision)]
        decisions = sorted(
            (i for i in reversed(eligible) if isinstance(i, Decision)), key=lambda i: i.origin_start_at, reverse=True
        )[:20]
        references = {f"{i.kind[0].upper()}{n}": i for n, i in enumerate([*open_work, *decisions], 1)}
        context = ExtractionContext(
            occurrence_id,
            series.title,
            occurrence.start_at,
            self.series.attendees(access.series_id),
            tuple(self.dictionary.list_entries(access.series_id)),
            tuple(sources),
            references,
            tuple(
                i
                for i in items
                if i.origin_occurrence_id == occurrence_id and (not i.extracted or i.human_updated_at is not None)
            ),
        )
        extracted = self.extractor.extract(context)
        applied = self.memory.apply_extraction(access, occurrence_id, extracted, input_at)
        if applied.stale:
            raise SeriesError(409, "stale_extraction")
        return ExtractionResult(
            applied.created,
            applied.closed,
            extracted.truncated,
            TeamMemoryUseCases(self.memory, self.series).board(access),
        )
