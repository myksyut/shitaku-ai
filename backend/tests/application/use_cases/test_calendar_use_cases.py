"""CalendarUseCases tests.

Tests for Calendar use cases following AAA pattern.
All external dependencies (GoogleCalendarClient, Repositories, RefreshGoogleTokenUseCase) are mocked.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.entities.google_integration import GoogleIntegration
from src.domain.entities.recurring_meeting import RecurringMeeting
from src.infrastructure.external.google_calendar_client import (
    CalendarAttendee,
    CalendarEvent,
)


class TestFetchRecurringMeetingsFromCalendarUseCase:
    """FetchRecurringMeetingsFromCalendarUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_returns_filtered_events(self) -> None:
        """Calendar APIからイベントを取得しフィルタリングする"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            FetchRecurringMeetingsFromCalendarUseCase,
        )

        user_id = uuid4()
        integration_id = uuid4()

        integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        events = [
            CalendarEvent(
                id="event1",
                summary="Weekly Standup",
                start=datetime.now(UTC),
                end=datetime.now(UTC),
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
            ),
        ]

        mock_google_repo = AsyncMock()
        mock_google_repo.get_by_id = AsyncMock(return_value=integration)

        mock_refresh_use_case = AsyncMock()
        mock_refresh_use_case.execute = AsyncMock(return_value="access_token")

        mock_calendar_client = MagicMock()
        mock_calendar_client.list_events = AsyncMock(return_value=events)

        mock_filter = MagicMock()
        mock_filter.filter_events = MagicMock(return_value=events)

        with (
            patch(
                "src.application.use_cases.calendar_use_cases.GoogleCalendarClient",
                return_value=mock_calendar_client,
            ),
            patch(
                "src.application.use_cases.calendar_use_cases.RecurringMeetingFilter",
                return_value=mock_filter,
            ),
        ):
            use_case = FetchRecurringMeetingsFromCalendarUseCase(
                google_repo=mock_google_repo,
                refresh_token_use_case=mock_refresh_use_case,
            )

            # Act
            result = await use_case.execute(user_id, integration_id)

            # Assert
            assert len(result) == 1
            assert result[0].summary == "Weekly Standup"
            mock_refresh_use_case.execute.assert_called_once_with(user_id, integration_id)
            mock_calendar_client.list_events.assert_called_once()
            mock_filter.filter_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_raises_when_integration_not_found(self) -> None:
        """連携が見つからない場合にValueErrorが発生する"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            FetchRecurringMeetingsFromCalendarUseCase,
        )

        user_id = uuid4()
        integration_id = uuid4()

        mock_google_repo = AsyncMock()
        mock_google_repo.get_by_id = AsyncMock(return_value=None)

        mock_refresh_use_case = AsyncMock()

        use_case = FetchRecurringMeetingsFromCalendarUseCase(
            google_repo=mock_google_repo,
            refresh_token_use_case=mock_refresh_use_case,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Integration not found"):
            await use_case.execute(user_id, integration_id)

    @pytest.mark.asyncio
    async def test_execute_raises_when_calendar_scope_missing(self) -> None:
        """Calendar読み取りスコープがない場合にValueErrorが発生する"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            FetchRecurringMeetingsFromCalendarUseCase,
        )

        user_id = uuid4()
        integration_id = uuid4()

        integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["openid", "email"],  # Missing calendar scope
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        mock_google_repo = AsyncMock()
        mock_google_repo.get_by_id = AsyncMock(return_value=integration)

        mock_refresh_use_case = AsyncMock()

        use_case = FetchRecurringMeetingsFromCalendarUseCase(
            google_repo=mock_google_repo,
            refresh_token_use_case=mock_refresh_use_case,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar scope not granted"):
            await use_case.execute(user_id, integration_id)


class TestSyncRecurringMeetingsUseCase:
    """SyncRecurringMeetingsUseCaseのテスト"""

    @pytest.mark.asyncio
    async def test_execute_creates_new_meetings(self) -> None:
        """新規定例MTGが作成される"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            SyncRecurringMeetingsUseCase,
        )

        user_id = uuid4()
        integration_id = uuid4()

        integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        events = [
            CalendarEvent(
                id="event1",
                summary="Weekly Standup",
                start=datetime.now(UTC),
                end=datetime.now(UTC),
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
            ),
        ]

        mock_google_repo = AsyncMock()
        mock_google_repo.get_by_id = AsyncMock(return_value=integration)

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_by_google_event_id = MagicMock(return_value=None)
        mock_meeting_repo.create = MagicMock(side_effect=lambda x: x)

        mock_refresh_use_case = AsyncMock()
        mock_refresh_use_case.execute = AsyncMock(return_value="access_token")

        mock_calendar_client = MagicMock()
        mock_calendar_client.list_events = AsyncMock(return_value=events)

        mock_filter = MagicMock()
        mock_filter.filter_events = MagicMock(return_value=events)

        with (
            patch(
                "src.application.use_cases.calendar_use_cases.GoogleCalendarClient",
                return_value=mock_calendar_client,
            ),
            patch(
                "src.application.use_cases.calendar_use_cases.RecurringMeetingFilter",
                return_value=mock_filter,
            ),
        ):
            use_case = SyncRecurringMeetingsUseCase(
                google_repo=mock_google_repo,
                meeting_repo=mock_meeting_repo,
                refresh_token_use_case=mock_refresh_use_case,
            )

            # Act
            result = await use_case.execute(user_id, integration_id)

            # Assert
            assert result.created == 1
            assert result.updated == 0
            mock_meeting_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_updates_existing_meetings(self) -> None:
        """既存定例MTGが更新される"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            SyncRecurringMeetingsUseCase,
        )

        user_id = uuid4()
        integration_id = uuid4()
        meeting_id = uuid4()

        integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        events = [
            CalendarEvent(
                id="event1",
                summary="Weekly Standup Updated",
                start=datetime.now(UTC),
                end=datetime.now(UTC),
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                attendees=[
                    CalendarAttendee(email="user1@example.com"),
                    CalendarAttendee(email="user2@example.com"),
                ],
            ),
        ]

        existing_meeting = RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id="event1",
            title="Weekly Standup",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            frequency="weekly",
            next_occurrence=datetime.now(UTC),
            created_at=datetime.now(UTC),
            attendees=["user1@example.com"],
        )

        mock_google_repo = AsyncMock()
        mock_google_repo.get_by_id = AsyncMock(return_value=integration)

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_by_google_event_id = MagicMock(return_value=existing_meeting)
        mock_meeting_repo.update = MagicMock(side_effect=lambda x: x)

        mock_refresh_use_case = AsyncMock()
        mock_refresh_use_case.execute = AsyncMock(return_value="access_token")

        mock_calendar_client = MagicMock()
        mock_calendar_client.list_events = AsyncMock(return_value=events)

        mock_filter = MagicMock()
        mock_filter.filter_events = MagicMock(return_value=events)

        with (
            patch(
                "src.application.use_cases.calendar_use_cases.GoogleCalendarClient",
                return_value=mock_calendar_client,
            ),
            patch(
                "src.application.use_cases.calendar_use_cases.RecurringMeetingFilter",
                return_value=mock_filter,
            ),
        ):
            use_case = SyncRecurringMeetingsUseCase(
                google_repo=mock_google_repo,
                meeting_repo=mock_meeting_repo,
                refresh_token_use_case=mock_refresh_use_case,
            )

            # Act
            result = await use_case.execute(user_id, integration_id)

            # Assert
            assert result.created == 0
            assert result.updated == 1
            mock_meeting_repo.update.assert_called_once()


class TestGetRecurringMeetingsUseCase:
    """GetRecurringMeetingsUseCaseのテスト"""

    def test_execute_returns_all_meetings(self) -> None:
        """ユーザーの全定例MTGが取得される"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            GetRecurringMeetingsUseCase,
        )

        user_id = uuid4()
        meetings = [
            RecurringMeeting(
                id=uuid4(),
                user_id=user_id,
                google_event_id="event1",
                title="Weekly Standup",
                rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
                frequency="weekly",
                next_occurrence=datetime.now(UTC),
                created_at=datetime.now(UTC),
                attendees=["user1@example.com"],
            ),
            RecurringMeeting(
                id=uuid4(),
                user_id=user_id,
                google_event_id="event2",
                title="Monthly Review",
                rrule="RRULE:FREQ=MONTHLY;BYMONTHDAY=1",
                frequency="monthly",
                next_occurrence=datetime.now(UTC),
                created_at=datetime.now(UTC),
                attendees=["user1@example.com"],
            ),
        ]

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_all = MagicMock(return_value=meetings)

        use_case = GetRecurringMeetingsUseCase(meeting_repo=mock_meeting_repo)

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 2
        assert result[0].title == "Weekly Standup"
        assert result[1].title == "Monthly Review"
        mock_meeting_repo.get_all.assert_called_once_with(user_id)

    def test_execute_returns_empty_list_when_no_meetings(self) -> None:
        """定例MTGがない場合は空リストが返される"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            GetRecurringMeetingsUseCase,
        )

        user_id = uuid4()

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_all = MagicMock(return_value=[])

        use_case = GetRecurringMeetingsUseCase(meeting_repo=mock_meeting_repo)

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert result == []


class TestLinkAgentToMeetingUseCase:
    """LinkAgentToMeetingUseCaseのテスト"""

    def test_execute_links_agent_to_meeting(self) -> None:
        """エージェントが定例MTGに紐付けられる"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            LinkAgentToMeetingUseCase,
        )

        user_id = uuid4()
        meeting_id = uuid4()
        agent_id = uuid4()

        meeting = RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id="event1",
            title="Weekly Standup",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            frequency="weekly",
            next_occurrence=datetime.now(UTC),
            created_at=datetime.now(UTC),
            attendees=["user1@example.com"],
            agent_id=None,
        )

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_by_id = MagicMock(return_value=meeting)
        mock_meeting_repo.update = MagicMock(side_effect=lambda x: x)

        use_case = LinkAgentToMeetingUseCase(meeting_repo=mock_meeting_repo)

        # Act
        result = use_case.execute(meeting_id, user_id, agent_id)

        # Assert
        assert result.agent_id == agent_id
        mock_meeting_repo.update.assert_called_once()

    def test_execute_raises_when_meeting_not_found(self) -> None:
        """定例MTGが見つからない場合にValueErrorが発生する"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            LinkAgentToMeetingUseCase,
        )

        user_id = uuid4()
        meeting_id = uuid4()
        agent_id = uuid4()

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_by_id = MagicMock(return_value=None)

        use_case = LinkAgentToMeetingUseCase(meeting_repo=mock_meeting_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="Meeting not found"):
            use_case.execute(meeting_id, user_id, agent_id)

    def test_execute_raises_when_agent_already_linked(self) -> None:
        """既にエージェントが紐付けられている場合にValueErrorが発生する"""
        # Arrange
        from src.application.use_cases.calendar_use_cases import (
            LinkAgentToMeetingUseCase,
        )

        user_id = uuid4()
        meeting_id = uuid4()
        existing_agent_id = uuid4()
        new_agent_id = uuid4()

        meeting = RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id="event1",
            title="Weekly Standup",
            rrule="RRULE:FREQ=WEEKLY;BYDAY=MO",
            frequency="weekly",
            next_occurrence=datetime.now(UTC),
            created_at=datetime.now(UTC),
            attendees=["user1@example.com"],
            agent_id=existing_agent_id,
        )

        mock_meeting_repo = MagicMock()
        mock_meeting_repo.get_by_id = MagicMock(return_value=meeting)

        use_case = LinkAgentToMeetingUseCase(meeting_repo=mock_meeting_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="Agent already linked"):
            use_case.execute(meeting_id, user_id, new_agent_id)
