from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
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
    )


@pytest.mark.parametrize("outcome", ["created", "already_member", "joined", "forbidden"])
async def test_claim_outcomes_recheck_the_callers_visibility(outcome: str) -> None:
    sid, uid = uuid4(), uuid4()
    repository = AsyncMock(spec=SeriesRepository)
    repository.get.return_value = make_series(sid, uid)
    repository.roles.side_effect = (
        [{sid: "member"}] if outcome == "already_member" else [{}, {sid: "member"} if outcome == "joined" else {}]
    )
    calendar = AsyncMock(spec=GoogleCalendarClient)
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
    credentials = AsyncMock(spec=SeriesCredentials)
    credentials.google_for_user.return_value = GoogleApis(
        calendar, MagicMock(spec=GoogleDriveClient), MagicMock(spec=GoogleDocsClient)
    )
    mirror = AsyncMock(spec=SeriesCalendarMirror)
    mirror.claim.return_value = sid if outcome == "created" else None
    use_case = CalendarUseCases(repository, credentials, mirror)
    if outcome == "forbidden":
        with pytest.raises(SeriesError) as error:
            await use_case.claim(uid, uuid4(), "event", frozenset({"member@example.com"}))
        assert error.value.status == 403
    else:
        assert await use_case.claim(uid, uuid4(), "event", frozenset({"member@example.com"})) == (outcome, sid)
    assert mirror.refresh_for_join.await_count == (1 if outcome in ("joined", "forbidden") else 0)


async def test_claim_rejects_unverified_participant_without_writing() -> None:
    calendar = AsyncMock(spec=GoogleCalendarClient)
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
    credentials = AsyncMock(spec=SeriesCredentials)
    credentials.google_for_user.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    mirror = AsyncMock(spec=SeriesCalendarMirror)
    with pytest.raises(SeriesError) as error:
        await CalendarUseCases(AsyncMock(spec=SeriesRepository), credentials, mirror).claim(
            uuid4(), uuid4(), "event", frozenset()
        )
    assert error.value.status == 422
    mirror.claim.assert_not_called()


@pytest.mark.parametrize("fresh", [True, False])
async def test_join_refresh_is_throttled_and_uses_creator_calendar(fresh: bool) -> None:
    series = make_series(uuid4(), uuid4(), datetime.now(UTC) - timedelta(seconds=30 if fresh else 180))
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        TypeAdapter(Series).dump_python(series, mode="json")
    ]
    credentials = AsyncMock(spec=SeriesCredentials)
    calendar = AsyncMock(spec=GoogleCalendarClient)
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
    await SeriesCalendarMirror(client, credentials).refresh_for_join("uid")
    assert credentials.google_for_series.await_count == (0 if fresh else 1)
    if not fresh:
        assert credentials.google_for_series.call_args.args == (series, "calendar")


async def test_access_dependency_hides_outsiders_and_distinguishes_members() -> None:
    repository = AsyncMock()
    sid, uid = uuid4(), uuid4()
    repository.roles.return_value = {}
    with pytest.raises(HTTPException) as missing:
        await member_access(sid, uid, repository)
    assert missing.value.status_code == 404
    repository.roles.return_value = {sid: "member"}
    access = await member_access(sid, uid, repository)
    with pytest.raises(HTTPException) as forbidden:
        creator_access(access)
    assert forbidden.value.status_code == 403
    repository.roles.return_value = {sid: "creator"}
    assert isinstance(await member_access(sid, uid, repository), CreatorAccess)
