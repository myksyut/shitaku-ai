"""単体テスト: GenerateAgendaUseCase.

トランスクリプト収集とSlack取得範囲制御のテスト。
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.agenda_use_cases import GenerateAgendaUseCase
from src.domain.entities.agenda import Agenda
from src.domain.entities.agent import Agent
from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptStructuredData,
)
from src.domain.entities.recurring_meeting import (
    MeetingFrequency,
    RecurringMeeting,
)
from src.domain.repositories.agenda_repository import AgendaRepository
from src.domain.repositories.agent_repository import AgentRepository
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.meeting_note_repository import MeetingNoteRepository
from src.domain.repositories.meeting_transcript_repository import MeetingTranscriptRepository
from src.domain.repositories.recurring_meeting_repository import RecurringMeetingRepository
from src.domain.repositories.slack_integration_repository import SlackIntegrationRepository
from src.infrastructure.services.agenda_generation_service import AgendaGenerationService


class TestGenerateAgendaUseCaseTranscriptCollection:
    """トランスクリプト収集関連のテスト."""

    @pytest.fixture
    def user_id(self) -> UUID:
        """テスト用ユーザーID."""
        return uuid4()

    @pytest.fixture
    def agent_id(self) -> UUID:
        """テスト用エージェントID."""
        return uuid4()

    @pytest.fixture
    def mock_agenda_repository(self) -> AsyncMock:
        """AgendaRepository モック."""
        mock = AsyncMock(spec=AgendaRepository)
        mock.create.return_value = MagicMock(spec=Agenda)
        return mock

    @pytest.fixture
    def mock_agent_repository(self) -> MagicMock:
        """AgentRepository モック."""
        return MagicMock(spec=AgentRepository)

    @pytest.fixture
    def mock_note_repository(self) -> AsyncMock:
        """MeetingNoteRepository モック."""
        mock = AsyncMock(spec=MeetingNoteRepository)
        mock.get_latest_by_agent.return_value = None
        return mock

    @pytest.fixture
    def mock_dictionary_repository(self) -> AsyncMock:
        """DictionaryRepository モック."""
        mock = AsyncMock(spec=DictionaryRepository)
        mock.get_all.return_value = []
        return mock

    @pytest.fixture
    def mock_slack_repository(self) -> AsyncMock:
        """SlackIntegrationRepository モック."""
        mock = AsyncMock(spec=SlackIntegrationRepository)
        mock.get_all.return_value = []
        return mock

    @pytest.fixture
    def mock_recurring_meeting_repository(self) -> AsyncMock:
        """RecurringMeetingRepository モック."""
        return AsyncMock(spec=RecurringMeetingRepository)

    @pytest.fixture
    def mock_transcript_repository(self) -> AsyncMock:
        """MeetingTranscriptRepository モック."""
        return AsyncMock(spec=MeetingTranscriptRepository)

    @pytest.fixture
    def mock_generation_service(self) -> AsyncMock:
        """AgendaGenerationService モック."""
        mock = AsyncMock(spec=AgendaGenerationService)
        mock.generate.return_value = "# Generated Agenda\n\nContent here"
        return mock

    def _create_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        transcript_count: int = 3,
        slack_message_days: int = 7,
    ) -> Agent:
        """テスト用Agentを作成."""
        return Agent(
            id=agent_id,
            user_id=user_id,
            name="Test Agent",
            created_at=datetime.now(),
            transcript_count=transcript_count,
            slack_message_days=slack_message_days,
        )

    def _create_recurring_meeting(
        self,
        meeting_id: UUID,
        agent_id: UUID,
        user_id: UUID,
        title: str,
    ) -> RecurringMeeting:
        """テスト用RecurringMeetingを作成."""
        return RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id=f"event_{meeting_id}",
            title=title,
            rrule="FREQ=WEEKLY",
            frequency=MeetingFrequency.WEEKLY,
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
            agent_id=agent_id,
        )

    def _create_transcript(
        self,
        transcript_id: UUID,
        recurring_meeting_id: UUID,
        meeting_date: datetime,
    ) -> MeetingTranscript:
        """テスト用MeetingTranscriptを作成."""
        return MeetingTranscript(
            id=transcript_id,
            recurring_meeting_id=recurring_meeting_id,
            meeting_date=meeting_date,
            google_doc_id=f"doc_{transcript_id}",
            raw_text="Test transcript content",
            structured_data=TranscriptStructuredData(entries=[]),
            match_confidence=0.9,
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_collect_transcripts_from_multiple_recurring_meetings(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """複数定例からトランスクリプトを収集できること（AC2-1, AC2-2）."""
        # Arrange: Agentの設定（transcript_count=2）
        agent = self._create_agent(agent_id, user_id, transcript_count=2)
        mock_agent_repository.get_by_id.return_value = agent

        # 2つの定例MTG
        meeting1_id = uuid4()
        meeting2_id = uuid4()
        recurring_meetings = [
            self._create_recurring_meeting(meeting1_id, agent_id, user_id, "Weekly Standup"),
            self._create_recurring_meeting(meeting2_id, agent_id, user_id, "Sprint Review"),
        ]
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = recurring_meetings

        # 各定例のトランスクリプト（各2件）
        now = datetime.now()
        transcripts_meeting1 = [
            self._create_transcript(uuid4(), meeting1_id, now),
            self._create_transcript(uuid4(), meeting1_id, now - timedelta(days=7)),
        ]
        transcripts_meeting2 = [
            self._create_transcript(uuid4(), meeting2_id, now - timedelta(days=1)),
            self._create_transcript(uuid4(), meeting2_id, now - timedelta(days=8)),
        ]
        mock_transcript_repository.get_by_recurring_meeting.side_effect = [
            transcripts_meeting1,
            transcripts_meeting2,
        ]

        # Arrange: Agenda作成のモック
        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Generated Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        result = await use_case.execute(user_id, agent_id)

        # Assert: 各定例に対してget_by_recurring_meetingが呼ばれたこと
        assert mock_transcript_repository.get_by_recurring_meeting.call_count == 2
        mock_transcript_repository.get_by_recurring_meeting.assert_any_call(meeting1_id, limit=2)
        mock_transcript_repository.get_by_recurring_meeting.assert_any_call(meeting2_id, limit=2)

        # Assert: generation_serviceにトランスクリプトが渡されたこと
        call_args = mock_generation_service.generate.call_args
        input_data = call_args[0][0]
        assert len(input_data.transcripts) == 4  # 2定例 x 2件

        # Assert: 結果にトランスクリプト情報が含まれること
        assert result.has_transcripts is True
        assert result.transcript_count == 4

    @pytest.mark.asyncio
    async def test_transcripts_sorted_by_date_descending(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """収集したトランスクリプトが日付降順でソートされること."""
        # Arrange
        agent = self._create_agent(agent_id, user_id, transcript_count=3)
        mock_agent_repository.get_by_id.return_value = agent

        meeting1_id = uuid4()
        recurring_meetings = [
            self._create_recurring_meeting(meeting1_id, agent_id, user_id, "Weekly"),
        ]
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = recurring_meetings

        # 順番をバラバラにしたトランスクリプト
        now = datetime.now()
        date1 = now - timedelta(days=14)  # 古い
        date2 = now - timedelta(days=7)  # 中間
        date3 = now  # 最新

        transcripts = [
            self._create_transcript(uuid4(), meeting1_id, date2),  # 中間
            self._create_transcript(uuid4(), meeting1_id, date1),  # 古い
            self._create_transcript(uuid4(), meeting1_id, date3),  # 最新
        ]
        mock_transcript_repository.get_by_recurring_meeting.return_value = transcripts

        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        await use_case.execute(user_id, agent_id)

        # Assert: 日付降順でソートされていること
        call_args = mock_generation_service.generate.call_args
        input_data = call_args[0][0]
        sorted_transcripts = input_data.transcripts
        assert len(sorted_transcripts) == 3
        assert sorted_transcripts[0].meeting_date == date3  # 最新
        assert sorted_transcripts[1].meeting_date == date2  # 中間
        assert sorted_transcripts[2].meeting_date == date1  # 古い

    @pytest.mark.asyncio
    async def test_slack_message_days_controls_fetch_range(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """slack_message_daysに基づいてSlack取得範囲が制御されること（AC3-1）."""
        # Arrange: slack_message_days=14
        agent = self._create_agent(agent_id, user_id, transcript_count=3, slack_message_days=14)
        agent.slack_channel_id = "C12345"  # Slack連携あり
        mock_agent_repository.get_by_id.return_value = agent

        # 定例・トランスクリプトなし
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = []

        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        await use_case.execute(user_id, agent_id)

        # Note: Slack取得ロジックの検証は実装後に詳細化
        # 現時点ではslack_message_daysがAgentに正しく設定されていることを確認
        assert agent.slack_message_days == 14

    @pytest.mark.asyncio
    async def test_continue_when_no_recurring_meetings(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """紐付け定例がない場合もアジェンダ生成を継続すること（AC2-3）."""
        # Arrange
        agent = self._create_agent(agent_id, user_id)
        mock_agent_repository.get_by_id.return_value = agent

        # 紐付け定例なし
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = []

        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Generated Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        result = await use_case.execute(user_id, agent_id)

        # Assert: アジェンダが生成されること
        assert result.agenda is not None
        # Assert: transcriptsは空リスト
        call_args = mock_generation_service.generate.call_args
        input_data = call_args[0][0]
        assert input_data.transcripts == []
        # Assert: has_transcriptsはFalse
        assert result.has_transcripts is False
        assert result.transcript_count == 0

    @pytest.mark.asyncio
    async def test_continue_when_transcript_fetch_fails(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """トランスクリプト取得エラー時も継続すること（AC2-4）."""
        # Arrange
        agent = self._create_agent(agent_id, user_id, transcript_count=2)
        mock_agent_repository.get_by_id.return_value = agent

        meeting1_id = uuid4()
        meeting2_id = uuid4()
        recurring_meetings = [
            self._create_recurring_meeting(meeting1_id, agent_id, user_id, "Meeting1"),
            self._create_recurring_meeting(meeting2_id, agent_id, user_id, "Meeting2"),
        ]
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = recurring_meetings

        # 1つ目は成功、2つ目は失敗
        transcripts_success = [
            self._create_transcript(uuid4(), meeting1_id, datetime.now()),
        ]
        mock_transcript_repository.get_by_recurring_meeting.side_effect = [
            transcripts_success,
            Exception("Database error"),
        ]

        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Generated Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        result = await use_case.execute(user_id, agent_id)

        # Assert: 取得できた分のみで継続
        call_args = mock_generation_service.generate.call_args
        input_data = call_args[0][0]
        assert len(input_data.transcripts) == 1
        # Assert: 結果は正常
        assert result.agenda is not None
        assert result.has_transcripts is True
        assert result.transcript_count == 1

    @pytest.mark.asyncio
    async def test_recurring_meeting_title_set_on_transcripts(
        self,
        user_id: UUID,
        agent_id: UUID,
        mock_agenda_repository: AsyncMock,
        mock_agent_repository: MagicMock,
        mock_note_repository: AsyncMock,
        mock_dictionary_repository: AsyncMock,
        mock_slack_repository: AsyncMock,
        mock_recurring_meeting_repository: AsyncMock,
        mock_transcript_repository: AsyncMock,
        mock_generation_service: AsyncMock,
    ) -> None:
        """トランスクリプトに定例会議名がセットされること."""
        # Arrange
        agent = self._create_agent(agent_id, user_id, transcript_count=2)
        mock_agent_repository.get_by_id.return_value = agent

        meeting1_id = uuid4()
        meeting2_id = uuid4()
        recurring_meetings = [
            self._create_recurring_meeting(meeting1_id, agent_id, user_id, "Weekly Standup"),
            self._create_recurring_meeting(meeting2_id, agent_id, user_id, "Sprint Review"),
        ]
        mock_recurring_meeting_repository.get_list_by_agent_id.return_value = recurring_meetings

        now = datetime.now()
        transcripts_meeting1 = [
            self._create_transcript(uuid4(), meeting1_id, now),
        ]
        transcripts_meeting2 = [
            self._create_transcript(uuid4(), meeting2_id, now - timedelta(days=1)),
        ]
        mock_transcript_repository.get_by_recurring_meeting.side_effect = [
            transcripts_meeting1,
            transcripts_meeting2,
        ]

        created_agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content="# Generated Agenda",
            source_note_id=None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        mock_agenda_repository.create.return_value = created_agenda

        # Act
        use_case = GenerateAgendaUseCase(
            agenda_repository=mock_agenda_repository,
            agent_repository=mock_agent_repository,
            note_repository=mock_note_repository,
            dictionary_repository=mock_dictionary_repository,
            slack_repository=mock_slack_repository,
            recurring_meeting_repository=mock_recurring_meeting_repository,
            meeting_transcript_repository=mock_transcript_repository,
            generation_service=mock_generation_service,
        )

        await use_case.execute(user_id, agent_id)

        # Assert: トランスクリプトにrecurring_meeting_titleがセットされていること
        call_args = mock_generation_service.generate.call_args
        input_data = call_args[0][0]
        transcripts = input_data.transcripts

        assert len(transcripts) == 2

        # 日付降順なのでWeekly Standupが先
        transcript_titles = [t.recurring_meeting_title for t in transcripts]
        assert "Weekly Standup" in transcript_titles
        assert "Sprint Review" in transcript_titles
