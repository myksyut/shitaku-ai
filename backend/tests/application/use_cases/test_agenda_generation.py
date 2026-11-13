from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.application.use_cases.agenda_use_cases import GenerateAgenda
from src.domain.entities.agenda import Agenda, AgendaTopic
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import CreatorAccess, Occurrence, SlackChannelRef
from src.domain.entities.team_memory import ActionItem
from src.infrastructure.external.slack_client import SlackMessageData
from src.infrastructure.services.agenda_generation_service import AgendaProposal
from tests.application.use_cases.test_series_use_cases import make_series


async def test_agenda_uses_bound_channels_newest_100_and_keeps_required_content() -> None:
    sid, owner, now = uuid4(), uuid4(), datetime.now(UTC)
    stored = replace(
        make_series(sid, owner),
        slack_integration_id=uuid4(),
        slack_channels=(SlackChannelRef("chosen-1", "one"), SlackChannelRef("chosen-2", "two")),
    )
    previous = Occurrence(
        uuid4(), sid, now - timedelta(days=3), now - timedelta(days=3), False, None, 0, None, 0, False
    )
    target = Occurrence(uuid4(), sid, now + timedelta(days=1), now + timedelta(days=1), False, None, 0, None, 0, False)
    series, content, memory, knowledge, dictionary, credentials, mirror, writer = (AsyncMock() for _ in range(8))
    series.get.return_value = stored
    series.occurrences.return_value = [previous, target]
    action = ActionItem(
        id=uuid4(),
        series_id=sid,
        body="Do not omit this action",
        origin_occurrence_id=uuid4(),
        origin_start_at=now - timedelta(days=10),
        extracted=True,
    )
    memory.list_items.return_value = [action]
    knowledge.for_occurrences.return_value = []
    dictionary.list_entries.return_value = []
    content.topics.return_value = [
        AgendaTopic(uuid4(), sid, target.id, uuid4(), "Member", "Do not omit this topic", None, now)
    ]
    slack = MagicMock()
    messages = [
        SlackMessageData(
            str((now - timedelta(hours=i + 1)).timestamp()), "Member", f"message-{i}", now - timedelta(hours=i + 1)
        )
        for i in range(100)
    ]
    slack.get_messages.return_value = messages
    credentials.slack_for_series.return_value = slack
    mirror.refresh.return_value = None
    writer.propose.return_value = AgendaProposal(None, False)

    async def save(access: CreatorAccess, oid: UUID, text: str) -> Agenda:
        return Agenda(oid, sid, text, now, now)

    content.save_generated.side_effect = save
    result = await GenerateAgenda(series, content, memory, knowledge, dictionary, credentials, mirror, writer).execute(
        CreatorAccess(sid, owner), target.id
    )
    assert "Do not omit this topic" in result.agenda.content
    assert "Do not omit this action" in result.agenda.content
    assert "1回持ち越し" in result.agenda.content
    assert result.sources.proposal_error == "llm_unavailable" and result.sources.truncated is False
    assert result.sources.slack_messages == 100
    assert result.sources.topics == 1 and result.sources.carried_action_items == 1
    assert [call.args[0] for call in slack.get_messages.call_args_list] == ["chosen-1", "chosen-2"]
    assert all(call.args[1] == previous.start_at for call in slack.get_messages.call_args_list)
    credentials.slack_for_series.assert_awaited_once_with(stored)
    context = writer.propose.call_args.args[0]
    assert len(context.slack) == 100
    assert context.actions[0].carry_over == 1


async def test_minutes_count_selects_documents_even_from_older_occurrences() -> None:
    sid, owner, now = uuid4(), uuid4(), datetime.now(UTC)
    stored = replace(make_series(sid, owner), minutes_count=2)
    previous = [
        Occurrence(uuid4(), sid, now - timedelta(days=days), now - timedelta(days=days), False, None, 0, None, 0, False)
        for days in (5, 4, 3, 2, 1)
    ]
    cancelled = Occurrence(uuid4(), sid, now, now, True, None, 0, None, 0, False)
    target = Occurrence(uuid4(), sid, now + timedelta(days=1), now + timedelta(days=1), False, None, 0, None, 0, False)
    notes = [
        Knowledge(
            uuid4(), sid, previous[1].id, "upload", None, None, "Old", "Older document", now - timedelta(hours=2)
        ),
        Knowledge(
            uuid4(), sid, previous[1].id, "upload", None, None, "New", "Newer document", now - timedelta(hours=1)
        ),
        Knowledge(
            uuid4(), sid, previous[1].id, "upload", None, None, "Oldest", "Oldest document", now - timedelta(hours=3)
        ),
        Knowledge(uuid4(), sid, cancelled.id, "upload", None, None, "Cancelled", "Not selected", now),
    ]
    series, content, memory, knowledge, dictionary, credentials, mirror, writer = (AsyncMock() for _ in range(8))
    series.get.return_value = stored
    series.occurrences.return_value = [*previous, cancelled, target]
    memory.list_items.return_value = []
    dictionary.list_entries.return_value = []
    content.topics.return_value = []
    content.save_generated.return_value = Agenda(target.id, sid, "", now, now)
    knowledge.for_occurrences.side_effect = lambda series_id, ids: [k for k in notes if k.occurrence_id in ids]
    mirror.refresh.return_value = None
    writer.propose.return_value = AgendaProposal(None, False)
    result = await GenerateAgenda(series, content, memory, knowledge, dictionary, credentials, mirror, writer).execute(
        CreatorAccess(sid, owner), target.id
    )
    knowledge.for_occurrences.assert_awaited_once_with(sid, [o.id for o in previous])
    assert [k.normalized_text for k in writer.propose.call_args.args[0].knowledge] == [
        "Newer document",
        "Older document",
    ]
    assert result.sources.knowledge == 2


async def test_agenda_generation_survives_calendar_mirror_database_errors() -> None:
    from postgrest.exceptions import APIError

    from src.domain.entities.series import CalendarSnapshot
    from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
    from src.infrastructure.external.series_credentials import GoogleApis

    sid, owner, now = uuid4(), uuid4(), datetime.now(UTC)
    target = Occurrence(uuid4(), sid, now, now, False, None, 0, None, 0, False)
    series, content, memory, knowledge, dictionary, credentials, writer = (AsyncMock() for _ in range(7))
    series.get.return_value = make_series(sid, owner)
    series.occurrences.return_value = [target]
    content.topics.return_value = []
    content.save_generated.return_value = Agenda(target.id, sid, "Saved", now, now)
    memory.list_items.return_value = []
    knowledge.for_occurrences.return_value = []
    dictionary.list_entries.return_value = []
    writer.propose.return_value = AgendaProposal(None, False)
    calendar = AsyncMock()
    calendar.snapshot.return_value = CalendarSnapshot(
        "uid", "event", "Weekly", None, (), False, (), now - timedelta(days=35), now + timedelta(days=35)
    )
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    service, started, failed = MagicMock(), MagicMock(), MagicMock()
    started.execute.return_value.data = True
    failed.execute.side_effect = APIError({"code": "XX000", "message": "Mirror unavailable", "details": "", "hint": ""})
    service.rpc.side_effect = [started, failed]
    result = await GenerateAgenda(
        series, content, memory, knowledge, dictionary, credentials, SeriesCalendarMirror(service, credentials), writer
    ).execute(CreatorAccess(sid, owner), target.id)
    assert result.agenda.content == "Saved" and result.sources.calendar_error == "calendar_unavailable"
    content.save_generated.assert_awaited_once()
