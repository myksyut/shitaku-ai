# Agent Reference Settings Integration Test - Design Doc: agent-reference-settings-design.md
# Generated: 2026-02-03 | Quota: 3/3 integration, 0/2 E2E
"""
アジェンダ生成参照情報設定機能の統合テスト

テスト対象: Agent参照設定（transcript_count, slack_message_days）
- 複数定例MTGからのトランスクリプト収集
- Slackメッセージ取得範囲の制御
- プロンプト生成への反映

関連ADR:
- ADR-0005: 1エージェント複数定例会議の紐付け対応
- ADR-0006: アジェンダ生成の参照情報設定
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.agenda_use_cases import GenerateAgendaUseCase
from src.domain.entities.agent import Agent
from src.domain.entities.meeting_transcript import MeetingTranscript
from src.domain.entities.recurring_meeting import MeetingFrequency, RecurringMeeting
from src.infrastructure.services.agenda_generation_service import (
    AgendaGenerationInput,
    AgendaGenerationService,
)


class TestAgentReferenceSettingsIntegration:
    """アジェンダ生成参照情報設定の統合テスト"""

    @pytest.fixture
    def user_id(self) -> UUID:
        """テスト用ユーザーID."""
        return uuid4()

    @pytest.fixture
    def agent_id(self) -> UUID:
        """テスト用エージェントID."""
        return uuid4()

    @pytest.fixture
    def setup_repositories(self) -> dict:
        """リポジトリとサービスのモックをセットアップ."""
        return {
            "agenda_repository": MagicMock(),
            "agent_repository": MagicMock(),
            "note_repository": MagicMock(),
            "dictionary_repository": MagicMock(),
            "slack_repository": MagicMock(),
            "generation_service": MagicMock(spec=AgendaGenerationService),
            "recurring_meeting_repository": MagicMock(),
            "meeting_transcript_repository": MagicMock(),
        }

    # AC: "When アジェンダ生成がリクエストされると、システムは全ての紐付け定例MTGから
    #     トランスクリプトを収集する"
    # AC: "When 複数定例が紐付けられている場合、システムは各定例から設定された件数の
    #     トランスクリプトを取得し、日付降順でソートする"
    # ROI: 99 | ビジネス価値: 10 | 頻度: 9
    # 振る舞い: アジェンダ生成リクエスト -> 複数定例取得 -> トランスクリプト収集 -> ソート -> 生成
    # @category: core-functionality
    # @dependency: GenerateAgendaUseCase, RecurringMeetingRepository,
    #              MeetingTranscriptRepository, AgendaGenerationService
    # @complexity: high
    #
    # 検証項目:
    # - 複数の定例MTGからトランスクリプトが収集される
    # - 各定例からtranscript_count件数分のトランスクリプトが取得される
    # - 全トランスクリプトが日付降順でソートされる
    # - 収集したトランスクリプトがアジェンダ生成に使用される
    @pytest.mark.asyncio
    async def test_collect_transcripts_from_multiple_recurring_meetings(
        self,
        user_id,
        agent_id,
        setup_repositories,
    ) -> None:
        """AC2-1/AC2-2: 複数定例MTGから設定件数分のトランスクリプトが日付降順で収集される"""
        repos = setup_repositories

        # Agent（transcript_count=2）
        agent = Agent(
            id=agent_id,
            user_id=user_id,
            name="Test Agent",
            created_at=datetime.now(),
            transcript_count=2,
            slack_message_days=7,
        )
        repos["agent_repository"].get_by_id.return_value = agent

        # 2つの定例MTG
        meeting1_id = uuid4()
        meeting2_id = uuid4()
        now = datetime.now()

        recurring_meetings = [
            RecurringMeeting(
                id=meeting1_id,
                user_id=user_id,
                title="Weekly Standup",
                google_event_id="event1",
                rrule="FREQ=WEEKLY",
                frequency=MeetingFrequency.WEEKLY,
                next_occurrence=now + timedelta(days=7),
                created_at=now,
                agent_id=agent_id,
            ),
            RecurringMeeting(
                id=meeting2_id,
                user_id=user_id,
                title="Sprint Review",
                google_event_id="event2",
                rrule="FREQ=BIWEEKLY",
                frequency=MeetingFrequency.BIWEEKLY,
                next_occurrence=now + timedelta(days=14),
                created_at=now,
                agent_id=agent_id,
            ),
        ]
        repos["recurring_meeting_repository"].get_list_by_agent_id = AsyncMock(return_value=recurring_meetings)

        # 各定例のトランスクリプト（2件ずつ）
        transcripts_meeting1 = [
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting1_id,
                meeting_date=now - timedelta(days=1),
                google_doc_id="doc1",
                raw_text="Standup Day 1",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
            ),
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting1_id,
                meeting_date=now - timedelta(days=8),
                google_doc_id="doc2",
                raw_text="Standup Day 8",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
            ),
        ]
        transcripts_meeting2 = [
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting2_id,
                meeting_date=now - timedelta(days=3),
                google_doc_id="doc3",
                raw_text="Sprint Review Week 1",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
            ),
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting2_id,
                meeting_date=now - timedelta(days=10),
                google_doc_id="doc4",
                raw_text="Sprint Review Week 2",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
            ),
        ]

        async def get_transcripts_side_effect(meeting_id, limit=None):
            if meeting_id == meeting1_id:
                return transcripts_meeting1
            if meeting_id == meeting2_id:
                return transcripts_meeting2
            return []

        repos["meeting_transcript_repository"].get_by_recurring_meeting = AsyncMock(
            side_effect=get_transcripts_side_effect
        )

        # 他の依存（MeetingNoteと辞書）
        repos["note_repository"].get_latest_by_agent = AsyncMock(return_value=None)
        repos["slack_repository"].get_all = AsyncMock(return_value=[])
        repos["dictionary_repository"].get_all = AsyncMock(return_value=[])

        # サービス
        repos["generation_service"].generate = AsyncMock(return_value="Generated Agenda")

        # AgendaRepository
        async def save_agenda(agenda):
            return agenda

        repos["agenda_repository"].create = AsyncMock(side_effect=save_agenda)

        # UseCase実行
        use_case = GenerateAgendaUseCase(**repos)
        result = await use_case.execute(user_id, agent_id)

        # 検証1: 各定例に対してget_by_recurring_meetingが呼ばれた
        assert repos["meeting_transcript_repository"].get_by_recurring_meeting.call_count == 2

        # 検証2: limit=2で呼ばれた
        calls = repos["meeting_transcript_repository"].get_by_recurring_meeting.call_args_list
        for call in calls:
            assert call.kwargs.get("limit") == 2

        # 検証3: 合計4件のトランスクリプトがサービスに渡された
        generate_call = repos["generation_service"].generate.call_args
        input_data: AgendaGenerationInput = generate_call[0][0]
        assert len(input_data.transcripts) == 4

        # 検証4: 日付降順でソートされている
        dates = [t.meeting_date for t in input_data.transcripts]
        assert dates == sorted(dates, reverse=True)

        # 検証5: トランスクリプトに定例MTG名がセットされている
        transcript_titles = [t.recurring_meeting_title for t in input_data.transcripts]
        assert "Weekly Standup" in transcript_titles
        assert "Sprint Review" in transcript_titles

        # 検証6: 結果に正しいトランスクリプト件数が含まれている
        assert result.has_transcripts is True
        assert result.transcript_count == 4

    # AC: "システムは収集したトランスクリプトをプロンプトに含め、
    #     「複数の定例MTGからのトランスクリプト」であることを明示する"
    # ROI: 89 | ビジネス価値: 9 | 頻度: 9
    # 振る舞い: トランスクリプト収集完了 -> プロンプト構築 -> トランスクリプトセクション追加 -> LLM呼び出し
    # @category: core-functionality
    # @dependency: AgendaGenerationService, BedrockClient
    # @complexity: medium
    #
    # 検証項目:
    # - プロンプトにトランスクリプトセクションが含まれる
    # - トランスクリプトの出所（どの定例MTGか）が明示される
    # - 日付情報がプロンプトに含まれる
    # - アジェンダが正常に生成される
    @pytest.mark.asyncio
    async def test_prompt_includes_transcripts_with_meeting_info(
        self,
        user_id,
        agent_id,
    ) -> None:
        """AC4-1: 収集したトランスクリプトが定例MTG情報付きでプロンプトに含まれる"""
        now = datetime.now()
        meeting_id = uuid4()

        # トランスクリプト（定例MTG名付き）
        transcripts = [
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting_id,
                meeting_date=datetime(2026, 2, 1, 10, 0),
                google_doc_id="doc1",
                raw_text="議題A: 進捗確認。決定事項: 来週完了予定。",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
                recurring_meeting_title="Weekly Standup",
            ),
            MeetingTranscript(
                id=uuid4(),
                recurring_meeting_id=meeting_id,
                meeting_date=datetime(2026, 1, 25, 10, 0),
                google_doc_id="doc2",
                raw_text="議題B: 設計レビュー。次回までに修正。",
                structured_data=None,
                match_confidence=0.9,
                created_at=now,
                recurring_meeting_title="Sprint Review",
            ),
        ]

        input_data = AgendaGenerationInput(
            latest_note=None,
            slack_messages=[],
            dictionary=[],
            transcripts=transcripts,
        )

        # AgendaGenerationServiceの_build_promptを直接テスト
        service = AgendaGenerationService()
        prompt = service._build_prompt(input_data)

        # 検証1: トランスクリプトセクションヘッダーが含まれる
        assert "過去のMTGトランスクリプト" in prompt

        # 検証2: 定例MTG名が含まれる
        assert "Weekly Standup" in prompt
        assert "Sprint Review" in prompt

        # 検証3: 日付が含まれる
        assert "2026/02/01" in prompt
        assert "2026/01/25" in prompt

        # 検証4: コンテンツが含まれる
        assert "議題A: 進捗確認" in prompt
        assert "議題B: 設計レビュー" in prompt

    # AC: "When アジェンダ生成時、システムはslack_message_daysで指定された日数分のメッセージを取得する"
    # ROI: 71 | ビジネス価値: 8 | 頻度: 8
    # 振る舞い: アジェンダ生成リクエスト -> slack_message_days取得 -> 日数分のメッセージ取得 -> 生成
    # @category: core-functionality
    # @dependency: GenerateAgendaUseCase, SlackClient
    # @complexity: medium
    #
    # 検証項目:
    # - slack_message_days設定値が読み取られる
    # - Slack APIが設定日数分の範囲で呼び出される
    # - 取得したメッセージがアジェンダ生成に使用される
    @pytest.mark.asyncio
    async def test_slack_messages_fetched_for_configured_days(
        self,
        user_id,
        agent_id,
        setup_repositories,
    ) -> None:
        """AC3-1: slack_message_daysで指定した日数分のSlackメッセージが取得される"""
        repos = setup_repositories
        now = datetime.now()

        # Agent（slack_message_days=14）
        agent = Agent(
            id=agent_id,
            user_id=user_id,
            name="Test Agent",
            created_at=now,
            transcript_count=3,
            slack_message_days=14,  # 14日分
            slack_channel_id="C123456",
        )
        repos["agent_repository"].get_by_id.return_value = agent

        # 定例なし（トランスクリプトなし）
        repos["recurring_meeting_repository"].get_list_by_agent_id = AsyncMock(return_value=[])

        # Slack連携あり
        slack_integration = MagicMock()
        slack_integration.encrypted_access_token = "encrypted_token"
        repos["slack_repository"].get_all = AsyncMock(return_value=[slack_integration])

        # 他の依存
        repos["note_repository"].get_latest_by_agent = AsyncMock(return_value=None)
        repos["dictionary_repository"].get_all = AsyncMock(return_value=[])
        repos["meeting_transcript_repository"].get_by_recurring_meeting = AsyncMock(return_value=[])

        # サービス
        repos["generation_service"].generate = AsyncMock(return_value="Generated Agenda")

        # AgendaRepository
        async def save_agenda(agenda):
            return agenda

        repos["agenda_repository"].create = AsyncMock(side_effect=save_agenda)

        # SlackClientとdecrypt_tokenをモック
        mock_slack_client = MagicMock()
        mock_slack_client.get_messages.return_value = []
        captured_oldest = None

        def capture_get_messages(channel_id, oldest):
            nonlocal captured_oldest
            captured_oldest = oldest
            return []

        mock_slack_client.get_messages.side_effect = capture_get_messages

        with (
            patch("src.application.use_cases.agenda_use_cases.decrypt_token", return_value="decrypted_token"),
            patch("src.application.use_cases.agenda_use_cases.SlackClient", return_value=mock_slack_client),
        ):
            # UseCase実行
            use_case = GenerateAgendaUseCase(**repos)
            await use_case.execute(user_id, agent_id)

        # 検証: Slack取得が14日前からになっている
        assert captured_oldest is not None
        expected_oldest = now - timedelta(days=14)
        # 秒単位の誤差を許容（テスト実行時間を考慮）
        assert abs((captured_oldest - expected_oldest).total_seconds()) < 60
