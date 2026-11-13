from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.use_cases.team_memory_use_cases import ExtractOccurrenceMemory
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import CreatorAccess, Occurrence
from src.domain.entities.team_memory import ActionItem, Decision, ExtractedMemory, ExtractionApplyResult
from tests.application.use_cases.test_series_use_cases import make_series


async def test_current_untouched_extraction_is_not_prompted_as_existing_references() -> None:
    sid, owner, oid, now = uuid4(), uuid4(), uuid4(), datetime.now(UTC)
    start = now - timedelta(days=1)
    current = ActionItem(
        id=uuid4(),
        series_id=sid,
        body="Current extraction",
        origin_occurrence_id=oid,
        origin_start_at=start,
        extracted=True,
    )
    decision = Decision(
        id=uuid4(),
        series_id=sid,
        body="Current decision",
        origin_occurrence_id=oid,
        origin_start_at=start,
        extracted=True,
    )
    human = replace(current, id=uuid4(), body="Human edit", human_updated_at=now)
    manual = replace(current, id=uuid4(), body="Manual entry", extracted=False)
    previous = replace(
        current,
        id=uuid4(),
        body="Previous extraction",
        origin_occurrence_id=uuid4(),
        origin_start_at=start - timedelta(days=1),
    )
    prior_decisions = [
        replace(decision, id=uuid4(), origin_occurrence_id=uuid4(), origin_start_at=start - timedelta(days=d))
        for d in range(1, 26)
    ]
    reversed_decision = replace(prior_decisions[0], id=uuid4(), resolution="reversed", closed_at=now)
    memory, series, knowledge, dictionary, extractor = (AsyncMock() for _ in range(5))
    series.get.return_value = make_series(sid, owner)
    series.occurrences.return_value = [Occurrence(oid, sid, start, start, False, None, 1, now, 0, False)]
    series.attendees.return_value = ()
    knowledge.for_occurrences.return_value = [Knowledge(uuid4(), sid, oid, "upload", None, None, "Notes", "Notes", now)]
    dictionary.list_entries.return_value = []
    memory.list_items.return_value = [current, decision, human, manual, previous, *prior_decisions, reversed_decision]
    memory.apply_extraction.return_value = ExtractionApplyResult(0, 0)
    extractor.extract.return_value = ExtractedMemory((), (), False)
    await ExtractOccurrenceMemory(memory, series, knowledge, dictionary, extractor).execute(
        CreatorAccess(sid, owner), oid
    )
    context = extractor.extract.call_args.args[0]
    assert {item.id for item in context.references.values()} == {
        human.id,
        manual.id,
        previous.id,
        *(item.id for item in prior_decisions[:20]),
    }
    assert {item.id for item in context.already_recorded} == {human.id, manual.id}
