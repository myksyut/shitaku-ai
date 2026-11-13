from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import TypeAdapter

from src.application.use_cases.series_use_cases import CalendarUseCases
from src.domain.entities.series import Attendee, CalendarSnapshot, CreatorAccess, Series, SeriesError
from src.domain.repositories.series_repository import SeriesRepository
from src.infrastructure.external.google_calendar_client import GoogleCalendarClient
from src.infrastructure.external.google_docs_client import GoogleDocsClient
from src.infrastructure.external.google_drive_client import GoogleDriveClient
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials
from src.presentation.api.v1.dependencies import creator_access, member_access


def make_series(sid: UUID, owner: UUID, synced: datetime | None = None) -> Series:
    return Series(
        sid,
        "uid",
        owner,
        "event",
        uuid4(),
        "Weekly",
        "RRULE:FREQ=WEEKLY",
        None,
        3,
        7,
        None,
        (),
        synced or datetime.now(UTC),
        None,
        calendar_refresh_attempted_at=synced,
    )


@pytest.mark.parametrize("outcome", ["created", "already_member", "joined", "forbidden"])
def test_claim_outcomes_recheck_the_callers_visibility(outcome: str) -> None:
    sid, uid = uuid4(), uuid4()
    repository = MagicMock(spec=SeriesRepository)
    repository.get.return_value = make_series(sid, uid)
    repository.roles.side_effect = (
        [{sid: "member"}] if outcome == "already_member" else [{}, {sid: "member"} if outcome == "joined" else {}]
    )
    calendar = MagicMock(spec=GoogleCalendarClient)
    calendar.snapshot.return_value = CalendarSnapshot(
        "uid",
        "event",
        "Weekly",
        "RRULE:FREQ=WEEKLY",
        (Attendee("member@example.com"),),
        False,
        (),
        datetime.now(UTC) - timedelta(days=35),
        datetime.now(UTC) + timedelta(days=35),
    )
    credentials = MagicMock(spec=SeriesCredentials)
    credentials.google_for_user.return_value = GoogleApis(
        calendar, MagicMock(spec=GoogleDriveClient), MagicMock(spec=GoogleDocsClient)
    )
    mirror = MagicMock(spec=SeriesCalendarMirror)
    mirror.claim.return_value = sid if outcome == "created" else None
    use_case = CalendarUseCases(repository, credentials, mirror)
    if outcome == "forbidden":
        with pytest.raises(SeriesError) as error:
            use_case.claim(uid, uuid4(), "event", frozenset({"member@example.com"}))
        assert error.value.status == 403
    else:
        assert use_case.claim(uid, uuid4(), "event", frozenset({"member@example.com"})) == (outcome, sid)
    assert mirror.refresh_for_join.call_count == (1 if outcome in ("joined", "forbidden") else 0)


def test_claim_rejects_unverified_participant_without_writing() -> None:
    calendar = MagicMock(spec=GoogleCalendarClient)
    calendar.snapshot.return_value = CalendarSnapshot(
        "uid",
        "event",
        "Weekly",
        "RRULE:FREQ=WEEKLY",
        (Attendee("b@example.com"),),
        False,
        (),
        datetime.now(UTC) - timedelta(days=35),
        datetime.now(UTC) + timedelta(days=35),
    )
    credentials = MagicMock(spec=SeriesCredentials)
    credentials.google_for_user.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    mirror = MagicMock(spec=SeriesCalendarMirror)
    with pytest.raises(SeriesError) as error:
        CalendarUseCases(MagicMock(spec=SeriesRepository), credentials, mirror).claim(
            uuid4(), uuid4(), "event", frozenset()
        )
    assert error.value.status == 422
    mirror.claim.assert_not_called()


@pytest.mark.parametrize("fresh", [True, False])
def test_join_refresh_is_throttled_and_uses_creator_calendar(fresh: bool) -> None:
    series = make_series(uuid4(), uuid4(), datetime.now(UTC) - timedelta(seconds=30 if fresh else 180))
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = True
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        TypeAdapter(Series).dump_python(series, mode="json")
    ]
    credentials = MagicMock(spec=SeriesCredentials)
    calendar = MagicMock(spec=GoogleCalendarClient)
    calendar.snapshot.return_value = CalendarSnapshot(
        "uid",
        "event",
        "Weekly",
        "RRULE:FREQ=WEEKLY",
        (),
        False,
        (),
        datetime.now(UTC) - timedelta(days=35),
        datetime.now(UTC) + timedelta(days=35),
    )
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    SeriesCalendarMirror(client, credentials).refresh_for_join("uid")
    assert credentials.google_for_series.call_count == (0 if fresh else 1)
    if not fresh:
        assert credentials.google_for_series.call_args.args == (series, "calendar")


def test_access_dependency_hides_outsiders_and_distinguishes_members() -> None:
    repository = MagicMock()
    sid, uid = uuid4(), uuid4()
    repository.roles.return_value = {}
    with pytest.raises(HTTPException) as missing:
        member_access(sid, uid, repository)
    assert missing.value.status_code == 404
    repository.roles.return_value = {sid: "member"}
    access = member_access(sid, uid, repository)
    with pytest.raises(HTTPException) as forbidden:
        creator_access(access)
    assert forbidden.value.status_code == 403
    repository.roles.return_value = {sid: "creator"}
    assert isinstance(member_access(sid, uid, repository), CreatorAccess)
