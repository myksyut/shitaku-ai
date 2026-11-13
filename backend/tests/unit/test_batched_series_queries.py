from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import TypeAdapter

from src.application.use_cases.series_use_cases import CalendarUseCases, SeriesUseCases
from src.domain.entities.series import CalendarSnapshot, Occurrence
from src.domain.repositories.series_repository import SeriesRepository
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from tests.client_fakes import as_service_client, as_user_client


def query_client() -> tuple[MagicMock, MagicMock]:
    client, query = MagicMock(), MagicMock()
    client.table.return_value = query
    client.rpc.return_value = query
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    return client, query


@pytest.mark.parametrize("count", [1, 100])
def test_series_summaries_use_one_query_independent_of_series_count(count: int) -> None:
    uid, other = uuid4(), uuid4()
    client, query = query_client()
    query.execute.return_value.data = [
        {
            "id": str(uuid4()),
            "title": f"Series {i}",
            "created_by": str(uid if i == 0 else other),
            "calendar_sync_error": None,
            "next_occurrence": None,
            "open_action_items": i,
        }
        for i in range(count)
    ]
    summaries = SeriesRepositoryImpl(as_user_client(client)).list_summaries(uid)
    assert len(summaries) == count and summaries[0].role == "creator"
    assert all(summary.role == "member" for summary in summaries[1:])
    client.table.assert_called_once_with("series_summary")
    query.execute.assert_called_once()
    client.rpc.assert_not_called()


def test_series_list_usecase_delegates_one_batched_read() -> None:
    repository = MagicMock(spec=SeriesRepository)
    repository.list_summaries.return_value = []
    uid = uuid4()
    assert SeriesUseCases(repository).list_for_caller(uid) == []
    repository.list_summaries.assert_called_once_with(uid)
    repository.get.assert_not_called()
    repository.occurrences.assert_not_called()


def test_calendar_choices_load_visible_ids_once_without_per_series_reads() -> None:
    repository = MagicMock(spec=SeriesRepository)
    visible_id, uid = uuid4(), uuid4()
    repository.visible_calendar_series.return_value = {"visible-uid": visible_id}
    now = datetime.now(UTC)
    first = CalendarSnapshot(
        "visible-uid", "event-one", "One", "RRULE:FREQ=WEEKLY", (), False, (), now, now + timedelta(days=35)
    )
    calendar = MagicMock()
    calendar.list_recurring_masters.return_value = [first, replace(first, ical_uid="hidden-uid", event_id="event-two")]
    credentials = MagicMock(spec=SeriesCredentials)
    credentials.google_for_user.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    choices = CalendarUseCases(repository, credentials, MagicMock(spec=SeriesCalendarMirror)).choices(uid, uuid4())
    assert [choice.series_id for choice in choices] == [visible_id, None]
    repository.visible_calendar_series.assert_called_once()
    repository.get.assert_not_called()
    repository.role_of_caller.assert_not_called()


def test_occurrence_lookup_is_one_series_and_id_scoped_query() -> None:
    sid, oid, now = uuid4(), uuid4(), datetime.now(UTC)
    occurrence = Occurrence(oid, sid, now, now, False, None, 0, None, 0, False)
    client, query = query_client()
    query.execute.return_value.data = [TypeAdapter(Occurrence).dump_python(occurrence, mode="json")]
    assert SeriesRepositoryImpl(as_user_client(client)).get_occurrence(sid, oid) == occurrence
    assert [call.args for call in query.eq.call_args_list] == [("series_id", str(sid)), ("id", str(oid))]
    query.execute.assert_called_once()


@pytest.mark.parametrize("created", [True, False])
def test_mirror_claim_always_returns_existing_or_created_series_identity(created: bool) -> None:
    sid, now = uuid4(), datetime.now(UTC)
    client, query = query_client()
    query.execute.return_value.data = [{"series_id": str(sid), "created": created}]
    snapshot = CalendarSnapshot(
        "uid", "event", "Weekly", "RRULE:FREQ=WEEKLY", (), False, (), now, now + timedelta(days=35)
    )
    result = SeriesCalendarMirror(as_service_client(client), MagicMock(spec=SeriesCredentials)).claim(
        snapshot, uuid4(), uuid4(), now
    )
    assert result.series_id == sid and result.created is created
    query.execute.assert_called_once()
