from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.infrastructure.external.google_calendar_client import CalendarEvent, GoogleCalendarClient, parse_snapshot


def test_snapshot_keeps_google_identity_and_drops_rooms() -> None:
    master = CalendarEvent.model_validate(
        {
            "id": "creator-id",
            "iCalUID": "shared-uid",
            "summary": "Weekly",
            "recurrence": ["RRULE:FREQ=WEEKLY"],
            "attendeesOmitted": True,
            "organizer": {"email": "OWNER@EXAMPLE.COM"},
            "attendees": [
                {"email": "Member@Example.com", "displayName": "Member"},
                {"email": "member@example.com", "displayName": "Same person"},
                {"email": "room@example.com", "resource": True},
                {"email": "room@resource.calendar.google.com"},
                {"email": "bad"},
            ],
        }
    )
    moved = CalendarEvent.model_validate(
        {
            "id": "instance",
            "originalStartTime": {"dateTime": "2026-11-01T10:00:00Z"},
            "start": {"dateTime": "2026-11-02T11:00:00Z"},
        }
    )
    cancelled = CalendarEvent.model_validate(
        {"id": "deleted", "status": "cancelled", "originalStartTime": {"date": "2026-11-08"}}
    )
    snapshot = parse_snapshot(
        master, [moved, cancelled], datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 12, 1, tzinfo=UTC)
    )
    assert snapshot.ical_uid == "shared-uid"
    assert snapshot.event_id == "creator-id"
    assert [a.email for a in snapshot.attendees] == ["member@example.com", "owner@example.com"]
    assert snapshot.attendees[-1].is_organizer
    assert snapshot.attendees_omitted
    assert snapshot.occurrences[0].original_start.day == 1
    assert snapshot.occurrences[0].start_at.day == 2
    assert snapshot.occurrences[1].is_cancelled
    assert snapshot.occurrences[1].start_at == datetime(2026, 11, 8, tzinfo=UTC)


@pytest.mark.parametrize("status", [404, 410])
async def test_missing_calendar_event_returns_none(status: int) -> None:
    response = httpx.Response(status, request=httpx.Request("GET", "https://calendar.test"))
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await GoogleCalendarClient("token").snapshot("gone", datetime.now(UTC)) is None


async def test_calendar_instances_are_paginated_and_include_cancelled() -> None:
    responses = [
        {"id": "event", "iCalUID": "uid", "recurrence": ["RRULE:FREQ=WEEKLY"]},
        {"items": [{"id": "one", "originalStartTime": {"dateTime": "2026-11-01T10:00:00Z"}}], "nextPageToken": "next"},
        {"items": [{"id": "two", "originalStartTime": {"dateTime": "2026-11-08T10:00:00Z"}, "status": "cancelled"}]},
    ]
    get = AsyncMock(
        side_effect=[
            httpx.Response(200, json=data, request=httpx.Request("GET", "https://calendar.test")) for data in responses
        ]
    )
    with patch("httpx.AsyncClient.get", new=get):
        snapshot = await GoogleCalendarClient("token").snapshot("event", datetime(2026, 11, 1, tzinfo=UTC))
    assert snapshot is not None and len(snapshot.occurrences) == 2
    assert get.call_args_list[1].kwargs["params"]["showDeleted"] == "true"
    assert get.call_args_list[2].kwargs["params"]["pageToken"] == "next"


async def test_cancelled_master_without_recurrence_is_missing() -> None:
    response = httpx.Response(
        200, json={"id": "gone", "status": "cancelled"}, request=httpx.Request("GET", "https://calendar.test")
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await GoogleCalendarClient("token").snapshot("gone", datetime.now(UTC)) is None
