"""CalendarUseCases tests.

Tests for SyncRecurringMeetingsUseCase including stale record deletion.
All external dependencies are mocked.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.use_cases import calendar_use_cases
from src.application.use_cases.calendar_use_cases import SyncRecurringMeetingsUseCase
from src.domain.entities.google_integration import GoogleIntegration
from src.infrastructure.external.google_calendar_client import (
    CalendarAttendee,
    CalendarEvent,
)
from src.infrastructure.external.google_oauth_client import GoogleTokenResponse


class TestSyncRecurringMeetingsUseCase:
    """SyncRecurringMeetingsUseCaseのテスト"""

    def _make_calendar_event(
        self,
        event_id: str = "event_1",
        summary: str = "Weekly Standup",
        status: str = "confirmed",
    ) -> CalendarEvent:
        """テスト用CalendarEventを作成するヘルパー"""
        return CalendarEvent(
            event_id=event_id,
            summary=summary,
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            attendees=[
                CalendarAttendee(email="a@test.com"),
                CalendarAttendee(email="b@test.com"),
            ],
            start_datetime=datetime(2026, 2, 10, 9, 0, tzinfo=UTC),
            status=status,
        )

    def _make_integration(self) -> GoogleIntegration:
        """テスト用GoogleIntegrationを作成するヘルパー"""
        return GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(UTC),
            updated_at=None,
        )

    @pytest.mark.asyncio
    async def test_execute_deletes_stale_meetings(self) -> None:
        """Google Calendarに存在しないDBレコードが削除されること"""
        # Arrange
        user_id = uuid4()
        integration = self._make_integration()
        events = [self._make_calendar_event(event_id="event_active")]

        mock_google_repo = AsyncMock()
        mock_google_repo.get_all.return_value = [integration]

        mock_meeting_repo = AsyncMock()
        mock_meeting_repo.get_by_google_event_id.return_value = None
        mock_meeting_repo.upsert.side_effect = lambda m: m
        mock_meeting_repo.delete_by_user_except_google_event_ids.return_value = 2

        mock_token_response = MagicMock(spec=GoogleTokenResponse)
        mock_token_response.access_token = "fake_access_token"

        with (
            patch.object(
                calendar_use_cases,
                "decrypt_google_token",
                return_value="decrypted_refresh_token",
            ),
            patch.object(
                calendar_use_cases,
                "GoogleOAuthClient",
            ) as mock_oauth_cls,
            patch.object(
                calendar_use_cases,
                "GoogleCalendarClient",
            ) as mock_calendar_cls,
        ):
            mock_oauth_instance = AsyncMock()
            mock_oauth_instance.refresh_access_token.return_value = mock_token_response
            mock_oauth_cls.return_value = mock_oauth_instance

            mock_calendar_instance = AsyncMock()
            mock_calendar_instance.get_recurring_events.return_value = events
            mock_calendar_cls.return_value = mock_calendar_instance

            use_case = SyncRecurringMeetingsUseCase(mock_google_repo, mock_meeting_repo)

            # Act
            result = await use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        mock_meeting_repo.delete_by_user_except_google_event_ids.assert_called_once_with(user_id, ["event_active"])

    @pytest.mark.asyncio
    async def test_execute_passes_empty_list_when_no_events(self) -> None:
        """Google Calendarにイベントがない場合、全DBレコードが削除対象になること"""
        # Arrange
        user_id = uuid4()
        integration = self._make_integration()

        mock_google_repo = AsyncMock()
        mock_google_repo.get_all.return_value = [integration]

        mock_meeting_repo = AsyncMock()
        mock_meeting_repo.delete_by_user_except_google_event_ids.return_value = 5

        mock_token_response = MagicMock(spec=GoogleTokenResponse)
        mock_token_response.access_token = "fake_access_token"

        with (
            patch.object(
                calendar_use_cases,
                "decrypt_google_token",
                return_value="decrypted_refresh_token",
            ),
            patch.object(
                calendar_use_cases,
                "GoogleOAuthClient",
            ) as mock_oauth_cls,
            patch.object(
                calendar_use_cases,
                "GoogleCalendarClient",
            ) as mock_calendar_cls,
        ):
            mock_oauth_instance = AsyncMock()
            mock_oauth_instance.refresh_access_token.return_value = mock_token_response
            mock_oauth_cls.return_value = mock_oauth_instance

            mock_calendar_instance = AsyncMock()
            mock_calendar_instance.get_recurring_events.return_value = []
            mock_calendar_cls.return_value = mock_calendar_instance

            use_case = SyncRecurringMeetingsUseCase(mock_google_repo, mock_meeting_repo)

            # Act
            result = await use_case.execute(user_id)

        # Assert
        assert len(result) == 0
        mock_meeting_repo.delete_by_user_except_google_event_ids.assert_called_once_with(user_id, [])

    @pytest.mark.asyncio
    async def test_execute_preserves_existing_agent_link_on_upsert(self) -> None:
        """既存レコードのagent_id紐付けがupsert時に保持されること"""
        # Arrange
        from src.domain.entities.recurring_meeting import (
            Attendee,
            MeetingFrequency,
            RecurringMeeting,
        )

        user_id = uuid4()
        agent_id = uuid4()
        meeting_id = uuid4()
        integration = self._make_integration()
        events = [self._make_calendar_event(event_id="event_linked")]

        existing_meeting = RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id="event_linked",
            title="Old Title",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            frequency=MeetingFrequency.WEEKLY,
            attendees=[Attendee(email="a@test.com")],
            next_occurrence=datetime(2026, 2, 10, 9, 0, tzinfo=UTC),
            agent_id=agent_id,
            created_at=datetime.now(UTC),
        )

        mock_google_repo = AsyncMock()
        mock_google_repo.get_all.return_value = [integration]

        mock_meeting_repo = AsyncMock()
        mock_meeting_repo.get_by_google_event_id.return_value = existing_meeting
        mock_meeting_repo.upsert.side_effect = lambda m: m
        mock_meeting_repo.delete_by_user_except_google_event_ids.return_value = 0

        mock_token_response = MagicMock(spec=GoogleTokenResponse)
        mock_token_response.access_token = "fake_access_token"

        with (
            patch.object(
                calendar_use_cases,
                "decrypt_google_token",
                return_value="decrypted_refresh_token",
            ),
            patch.object(
                calendar_use_cases,
                "GoogleOAuthClient",
            ) as mock_oauth_cls,
            patch.object(
                calendar_use_cases,
                "GoogleCalendarClient",
            ) as mock_calendar_cls,
        ):
            mock_oauth_instance = AsyncMock()
            mock_oauth_instance.refresh_access_token.return_value = mock_token_response
            mock_oauth_cls.return_value = mock_oauth_instance

            mock_calendar_instance = AsyncMock()
            mock_calendar_instance.get_recurring_events.return_value = events
            mock_calendar_cls.return_value = mock_calendar_instance

            use_case = SyncRecurringMeetingsUseCase(mock_google_repo, mock_meeting_repo)

            # Act
            result = await use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        upserted_meeting = mock_meeting_repo.upsert.call_args[0][0]
        assert upserted_meeting.agent_id == agent_id
        assert upserted_meeting.id == meeting_id
