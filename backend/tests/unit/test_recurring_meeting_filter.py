"""RecurringMeetingFilter unit tests.

AC6, AC7, AC8の条件を検証するテスト。
TDD: Red Phase - テストを先に作成。
"""

from datetime import UTC, datetime, timedelta

from src.domain.services.recurring_meeting_filter import (
    RecurringMeetingFilter,
    has_minimum_attendees,
    has_recent_occurrence,
    is_valid_rrule,
    parse_frequency_from_rrule,
)
from src.infrastructure.external.google_calendar_client import (
    CalendarAttendee,
    CalendarEvent,
    CalendarOrganizer,
)


class TestRRULEValidation:
    """AC6: RRULEイベントのみ検出のテスト."""

    def test_is_valid_rrule_with_weekly_rule(self) -> None:
        """毎週のRRULEは有効."""
        assert is_valid_rrule(["RRULE:FREQ=WEEKLY;BYDAY=MO"]) is True

    def test_is_valid_rrule_with_biweekly_rule(self) -> None:
        """隔週のRRULEは有効."""
        assert is_valid_rrule(["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=WE"]) is True

    def test_is_valid_rrule_with_monthly_rule(self) -> None:
        """月次のRRULEは有効."""
        assert is_valid_rrule(["RRULE:FREQ=MONTHLY;BYMONTHDAY=1"]) is True

    def test_is_valid_rrule_with_none(self) -> None:
        """RRULEがない場合は無効."""
        assert is_valid_rrule(None) is False

    def test_is_valid_rrule_with_empty_list(self) -> None:
        """空のRRULEリストは無効."""
        assert is_valid_rrule([]) is False

    def test_is_valid_rrule_with_daily_rule(self) -> None:
        """毎日のRRULEは定例MTGとして無効（フィルタ対象外）."""
        assert is_valid_rrule(["RRULE:FREQ=DAILY"]) is False


class TestAttendeeValidation:
    """AC7: 参加者2人以上のみのテスト."""

    def test_has_minimum_attendees_with_two_attendees(self) -> None:
        """参加者2人は有効."""
        attendees = [
            CalendarAttendee(email="user1@example.com"),
            CalendarAttendee(email="user2@example.com"),
        ]
        assert has_minimum_attendees(attendees, minimum=2) is True

    def test_has_minimum_attendees_with_one_attendee(self) -> None:
        """参加者1人は無効."""
        attendees = [CalendarAttendee(email="user1@example.com")]
        assert has_minimum_attendees(attendees, minimum=2) is False

    def test_has_minimum_attendees_with_empty_list(self) -> None:
        """参加者なしは無効."""
        assert has_minimum_attendees([], minimum=2) is False

    def test_has_minimum_attendees_with_none(self) -> None:
        """参加者がNoneの場合は無効."""
        assert has_minimum_attendees(None, minimum=2) is False


class TestRecentOccurrence:
    """AC8: 過去3ヶ月以内に実績ありのテスト."""

    def test_has_recent_occurrence_within_3_months(self) -> None:
        """過去3ヶ月以内の開催は有効."""
        now = datetime.now(UTC)
        two_months_ago = now - timedelta(days=60)
        assert has_recent_occurrence(two_months_ago, months=3) is True

    def test_has_recent_occurrence_exactly_3_months(self) -> None:
        """ちょうど3ヶ月前（90日前）は有効."""
        now = datetime.now(UTC)
        # 境界条件: 89日前は確実に有効
        just_under_3_months = now - timedelta(days=89)
        assert has_recent_occurrence(just_under_3_months, months=3) is True

    def test_has_recent_occurrence_over_3_months(self) -> None:
        """3ヶ月以上前は無効."""
        now = datetime.now(UTC)
        four_months_ago = now - timedelta(days=120)
        assert has_recent_occurrence(four_months_ago, months=3) is False


class TestParseFrequency:
    """RRULEから頻度を解析するテスト."""

    def test_parse_weekly_frequency(self) -> None:
        """週次のRRULEからweeklyを解析."""
        assert parse_frequency_from_rrule(["RRULE:FREQ=WEEKLY;BYDAY=MO"]) == "weekly"

    def test_parse_biweekly_frequency(self) -> None:
        """隔週のRRULEからbiweeklyを解析."""
        assert parse_frequency_from_rrule(["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=WE"]) == "biweekly"

    def test_parse_monthly_frequency(self) -> None:
        """月次のRRULEからmonthlyを解析."""
        assert parse_frequency_from_rrule(["RRULE:FREQ=MONTHLY;BYMONTHDAY=1"]) == "monthly"


class TestRecurringMeetingFilter:
    """RecurringMeetingFilterの統合テスト."""

    def test_filter_events_applies_all_conditions(self) -> None:
        """全条件を満たすイベントのみがフィルタされる."""
        now = datetime.now(UTC)

        events = [
            # 有効: RRULE あり、参加者2人、最近開催
            CalendarEvent(
                id="event1",
                summary="Valid Meeting",
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                start=now - timedelta(days=7),
                end=now - timedelta(days=7) + timedelta(hours=1),
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
            # 無効: RRULE なし
            CalendarEvent(
                id="event2",
                summary="No RRULE",
                recurrence=None,
                start=now - timedelta(days=7),
                end=now - timedelta(days=7) + timedelta(hours=1),
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
            # 無効: 参加者1人
            CalendarEvent(
                id="event3",
                summary="One Attendee",
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=TU"],
                start=now - timedelta(days=7),
                end=now - timedelta(days=7) + timedelta(hours=1),
                attendees=[CalendarAttendee(email="user1@example.com")],
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
        ]

        filter_service = RecurringMeetingFilter()
        filtered = filter_service.filter_events(events)

        assert len(filtered) == 1
        assert filtered[0].id == "event1"

    def test_filter_events_excludes_daily_rrule(self) -> None:
        """毎日のRRULEは除外される."""
        now = datetime.now(UTC)

        events = [
            CalendarEvent(
                id="daily_event",
                summary="Daily Meeting",
                recurrence=["RRULE:FREQ=DAILY"],
                start=now - timedelta(days=1),
                end=now - timedelta(days=1) + timedelta(hours=1),
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
        ]

        filter_service = RecurringMeetingFilter()
        filtered = filter_service.filter_events(events)

        assert len(filtered) == 0

    def test_filter_events_excludes_old_events(self) -> None:
        """3ヶ月以上前のイベントは除外される."""
        now = datetime.now(UTC)

        events = [
            CalendarEvent(
                id="old_event",
                summary="Old Meeting",
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                start=now - timedelta(days=120),
                end=now - timedelta(days=120) + timedelta(hours=1),
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
        ]

        filter_service = RecurringMeetingFilter()
        filtered = filter_service.filter_events(events)

        assert len(filtered) == 0

    def test_filter_events_with_none_attendees(self) -> None:
        """参加者がNoneのイベントは除外される."""
        now = datetime.now(UTC)

        events = [
            CalendarEvent(
                id="no_attendees",
                summary="No Attendees Meeting",
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                start=now - timedelta(days=7),
                end=now - timedelta(days=7) + timedelta(hours=1),
                attendees=None,
                organizer=CalendarOrganizer(email="organizer@example.com"),
            ),
        ]

        filter_service = RecurringMeetingFilter()
        filtered = filter_service.filter_events(events)

        assert len(filtered) == 0
