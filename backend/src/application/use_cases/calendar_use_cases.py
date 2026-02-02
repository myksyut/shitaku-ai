"""Use cases for Google Calendar operations.

Following ADR-0001 clean architecture and existing google_auth_use_cases.py patterns.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from src.application.use_cases.google_auth_use_cases import RefreshGoogleTokenUseCase
from src.domain.entities.recurring_meeting import MeetingFrequency, RecurringMeeting
from src.domain.repositories.google_integration_repository import (
    GoogleIntegrationRepository,
)
from src.domain.repositories.recurring_meeting_repository import (
    RecurringMeetingRepository,
)
from src.domain.services.recurring_meeting_filter import (
    RecurringMeetingFilter,
    parse_frequency_from_rrule,
)
from src.infrastructure.external.google_calendar_client import (
    CalendarEvent,
    GoogleCalendarClient,
)

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


@dataclass
class SyncResult:
    """同期結果."""

    created: int
    updated: int


class FetchRecurringMeetingsFromCalendarUseCase:
    """Calendar APIから定例MTGを取得・フィルタリングするユースケース."""

    def __init__(
        self,
        google_repo: GoogleIntegrationRepository,
        refresh_token_use_case: RefreshGoogleTokenUseCase,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            google_repo: Google連携リポジトリ.
            refresh_token_use_case: トークンリフレッシュユースケース.
        """
        self.google_repo = google_repo
        self.refresh_token_use_case = refresh_token_use_case

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
    ) -> list[CalendarEvent]:
        """Calendar APIから定例MTGを取得・フィルタリングする.

        Args:
            user_id: ユーザーID.
            integration_id: Google連携ID.

        Returns:
            フィルタリングされた定例MTGイベントリスト.

        Raises:
            ValueError: 連携が見つからない場合、またはスコープが不足している場合.
        """
        # 連携を取得
        integration = await self.google_repo.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # Calendarスコープを確認
        if not integration.has_scope(CALENDAR_SCOPE):
            raise ValueError("Calendar scope not granted")

        # アクセストークンを取得
        access_token = await self.refresh_token_use_case.execute(user_id, integration_id)

        # Calendar APIからイベントを取得
        client = GoogleCalendarClient(access_token)
        events = await client.list_events()

        # フィルタリング
        filter_service = RecurringMeetingFilter()
        return filter_service.filter_events(events)


class SyncRecurringMeetingsUseCase:
    """Calendar APIから定例MTGを取得してDBに同期するユースケース."""

    def __init__(
        self,
        google_repo: GoogleIntegrationRepository,
        meeting_repo: RecurringMeetingRepository,
        refresh_token_use_case: RefreshGoogleTokenUseCase,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            google_repo: Google連携リポジトリ.
            meeting_repo: 定例MTGリポジトリ.
            refresh_token_use_case: トークンリフレッシュユースケース.
        """
        self.google_repo = google_repo
        self.meeting_repo = meeting_repo
        self.refresh_token_use_case = refresh_token_use_case

    async def execute(
        self,
        user_id: UUID,
        integration_id: UUID,
    ) -> SyncResult:
        """Calendar APIから定例MTGを取得してDBに同期する.

        Args:
            user_id: ユーザーID.
            integration_id: Google連携ID.

        Returns:
            SyncResult with created and updated counts.

        Raises:
            ValueError: 連携が見つからない場合、またはスコープが不足している場合.
        """
        # 連携を取得
        integration = await self.google_repo.get_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        # Calendarスコープを確認
        if not integration.has_scope(CALENDAR_SCOPE):
            raise ValueError("Calendar scope not granted")

        # アクセストークンを取得
        access_token = await self.refresh_token_use_case.execute(user_id, integration_id)

        # Calendar APIからイベントを取得
        client = GoogleCalendarClient(access_token)
        events = await client.list_events()

        # フィルタリング
        filter_service = RecurringMeetingFilter()
        filtered_events = filter_service.filter_events(events)

        # DBに同期
        created = 0
        updated = 0

        for event in filtered_events:
            existing = self.meeting_repo.get_by_google_event_id(event.id, user_id)

            if existing:
                # 既存の定例MTGを更新
                self._update_meeting_from_event(existing, event)
                self.meeting_repo.update(existing)
                updated += 1
            else:
                # 新規作成
                meeting = self._create_meeting_from_event(user_id, event)
                self.meeting_repo.create(meeting)
                created += 1

        return SyncResult(created=created, updated=updated)

    def _create_meeting_from_event(
        self,
        user_id: UUID,
        event: CalendarEvent,
    ) -> RecurringMeeting:
        """CalendarEventからRecurringMeetingを作成する."""
        rrule = event.recurrence[0] if event.recurrence else ""
        frequency = cast(MeetingFrequency, parse_frequency_from_rrule(event.recurrence or []))
        attendees = [a.email for a in (event.attendees or [])]

        return RecurringMeeting(
            id=uuid4(),
            user_id=user_id,
            google_event_id=event.id,
            title=event.summary,
            rrule=rrule,
            frequency=frequency,
            next_occurrence=event.start,
            created_at=datetime.now(),
            attendees=attendees,
        )

    def _update_meeting_from_event(
        self,
        meeting: RecurringMeeting,
        event: CalendarEvent,
    ) -> None:
        """CalendarEventから既存のRecurringMeetingを更新する."""
        attendees = [a.email for a in (event.attendees or [])]
        meeting.update_attendees(attendees)
        meeting.update_next_occurrence(event.start)


class GetRecurringMeetingsUseCase:
    """DBから定例MTG一覧を取得するユースケース."""

    def __init__(self, meeting_repo: RecurringMeetingRepository) -> None:
        """Initialize use case with repository.

        Args:
            meeting_repo: 定例MTGリポジトリ.
        """
        self.meeting_repo = meeting_repo

    def execute(self, user_id: UUID) -> list[RecurringMeeting]:
        """ユーザーの全定例MTGを取得する.

        Args:
            user_id: ユーザーID.

        Returns:
            RecurringMeetingエンティティのリスト.
        """
        return self.meeting_repo.get_all(user_id)


class LinkAgentToMeetingUseCase:
    """エージェントを定例MTGに紐付けるユースケース."""

    def __init__(self, meeting_repo: RecurringMeetingRepository) -> None:
        """Initialize use case with repository.

        Args:
            meeting_repo: 定例MTGリポジトリ.
        """
        self.meeting_repo = meeting_repo

    def execute(
        self,
        meeting_id: UUID,
        user_id: UUID,
        agent_id: UUID,
    ) -> RecurringMeeting:
        """エージェントを定例MTGに紐付ける.

        Args:
            meeting_id: 定例MTGのID.
            user_id: ユーザーID.
            agent_id: 紐付けるエージェントのID.

        Returns:
            更新されたRecurringMeetingエンティティ.

        Raises:
            ValueError: 定例MTGが見つからない場合、または既にエージェントが紐付いている場合.
        """
        meeting = self.meeting_repo.get_by_id(meeting_id, user_id)
        if not meeting:
            raise ValueError("Meeting not found")

        if meeting.agent_id is not None:
            raise ValueError("Agent already linked")

        meeting.link_agent(agent_id)
        return self.meeting_repo.update(meeting)
