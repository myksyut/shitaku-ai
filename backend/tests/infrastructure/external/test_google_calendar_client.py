"""GoogleCalendarClient tests.

Tests for cancelled event filtering and status parsing.
All external dependencies (httpx) are mocked.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.external.google_calendar_client import (
    CalendarEvent,
    GoogleCalendarClient,
)


class TestCalendarEventStatus:
    """CalendarEventのstatus属性テスト"""

    def test_default_status_is_confirmed(self) -> None:
        """デフォルトのstatusがconfirmedであること"""
        event = CalendarEvent(
            event_id="test_id",
            summary="Test Meeting",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            attendees=[],
            start_datetime=datetime.now(UTC),
        )
        assert event.status == "confirmed"

    def test_status_can_be_set_to_cancelled(self) -> None:
        """statusをcancelledに設定できること"""
        event = CalendarEvent(
            event_id="test_id",
            summary="Test Meeting",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            attendees=[],
            start_datetime=datetime.now(UTC),
            status="cancelled",
        )
        assert event.status == "cancelled"


class TestParseEventStatus:
    """_parse_eventのstatus取得テスト"""

    def test_parse_event_extracts_confirmed_status(self) -> None:
        """confirmedステータスのイベントをパースできること"""
        client = GoogleCalendarClient("fake_token")
        item = {
            "id": "event_123",
            "summary": "Weekly Standup",
            "status": "confirmed",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
            "start": {"dateTime": "2026-01-15T09:00:00+09:00"},
            "attendees": [],
        }
        event = client._parse_event(item)
        assert event is not None
        assert event.status == "confirmed"

    def test_parse_event_extracts_cancelled_status(self) -> None:
        """cancelledステータスのイベントをパースできること"""
        client = GoogleCalendarClient("fake_token")
        item = {
            "id": "event_456",
            "summary": "Cancelled Meeting",
            "status": "cancelled",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TU"],
            "start": {"dateTime": "2026-01-15T10:00:00+09:00"},
            "attendees": [],
        }
        event = client._parse_event(item)
        assert event is not None
        assert event.status == "cancelled"

    def test_parse_event_defaults_to_confirmed_when_no_status(self) -> None:
        """statusフィールドがない場合、confirmedがデフォルトになること"""
        client = GoogleCalendarClient("fake_token")
        item = {
            "id": "event_789",
            "summary": "No Status Meeting",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=WE"],
            "start": {"dateTime": "2026-01-15T11:00:00+09:00"},
            "attendees": [],
        }
        event = client._parse_event(item)
        assert event is not None
        assert event.status == "confirmed"


class TestGetRecurringEventsFiltersExceptionInstances:
    """get_recurring_eventsの例外インスタンスフィルタリングテスト"""

    @pytest.mark.asyncio
    async def test_exception_instances_are_filtered_out(self) -> None:
        """recurringEventIdを持つ例外インスタンスがフィルタリングされること"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "base_event_123",
                    "summary": "Weekly Standup",
                    "status": "confirmed",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                    "start": {"dateTime": "2026-01-15T09:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
                {
                    "id": "base_event_123_R20260122T090000",
                    "summary": "Weekly Standup",
                    "status": "confirmed",
                    "recurringEventId": "base_event_123",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                    "start": {"dateTime": "2026-01-22T09:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
            ],
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = GoogleCalendarClient("fake_token")

        with patch("src.infrastructure.external.google_calendar_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            events = await client.get_recurring_events(min_attendees=2)

        # Assert: only the base event should be returned
        assert len(events) == 1
        assert events[0].event_id == "base_event_123"


class TestGetRecurringEventsPagination:
    """get_recurring_eventsのページネーションテスト"""

    @pytest.mark.asyncio
    async def test_fetches_all_pages(self) -> None:
        """nextPageTokenがある場合に全ページを取得すること"""
        # Arrange
        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "items": [
                {
                    "id": "event_page1",
                    "summary": "Page 1 Meeting",
                    "status": "confirmed",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                    "start": {"dateTime": "2026-01-15T09:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
            ],
            "nextPageToken": "token_page2",
        }

        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "items": [
                {
                    "id": "event_page2",
                    "summary": "Page 2 Meeting",
                    "status": "confirmed",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TU"],
                    "start": {"dateTime": "2026-01-16T10:00:00+09:00"},
                    "attendees": [
                        {"email": "c@test.com"},
                        {"email": "d@test.com"},
                    ],
                },
            ],
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=[page1_response, page2_response])

        client = GoogleCalendarClient("fake_token")

        with patch("src.infrastructure.external.google_calendar_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            events = await client.get_recurring_events(min_attendees=2)

        # Assert: events from both pages should be returned
        assert len(events) == 2
        assert events[0].event_id == "event_page1"
        assert events[1].event_id == "event_page2"
        assert mock_http_client.get.call_count == 2


class TestGetRecurringEventsFiltersCancelled:
    """get_recurring_eventsのcancelledイベントフィルタリングテスト"""

    @pytest.mark.asyncio
    async def test_cancelled_events_are_filtered_out(self) -> None:
        """cancelledイベントがフィルタリングされること"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "confirmed_event",
                    "summary": "Active Weekly",
                    "status": "confirmed",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                    "start": {"dateTime": "2026-01-15T09:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
                {
                    "id": "cancelled_event",
                    "summary": "Cancelled Weekly",
                    "status": "cancelled",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TU"],
                    "start": {"dateTime": "2026-01-15T10:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
            ]
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = GoogleCalendarClient("fake_token")

        with patch("src.infrastructure.external.google_calendar_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            events = await client.get_recurring_events(min_attendees=2)

        # Assert
        assert len(events) == 1
        assert events[0].event_id == "confirmed_event"
        assert events[0].status == "confirmed"

    @pytest.mark.asyncio
    async def test_tentative_events_are_not_filtered(self) -> None:
        """tentativeイベントはフィルタリングされないこと"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "tentative_event",
                    "summary": "Tentative Weekly",
                    "status": "tentative",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=FR"],
                    "start": {"dateTime": "2026-01-17T14:00:00+09:00"},
                    "attendees": [
                        {"email": "a@test.com"},
                        {"email": "b@test.com"},
                    ],
                },
            ]
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = GoogleCalendarClient("fake_token")

        with patch("src.infrastructure.external.google_calendar_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            events = await client.get_recurring_events(min_attendees=2)

        # Assert
        assert len(events) == 1
        assert events[0].status == "tentative"
