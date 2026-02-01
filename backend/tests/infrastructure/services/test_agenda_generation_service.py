"""Unit tests for AgendaGenerationService.

Tests for agenda generation prompt building and service behavior.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.entities.meeting_note import MeetingNote
from src.infrastructure.external.slack_client import SlackMessageData
from src.infrastructure.services.agenda_generation_service import (
    AgendaGenerationInput,
    AgendaGenerationService,
)


class TestAgendaGenerationServicePromptBuilding:
    """Test AgendaGenerationService._build_prompt method."""

    def test_build_prompt_with_all_sources(self) -> None:
        """全てのデータソースがある場合のプロンプト構築"""
        # Arrange
        service = AgendaGenerationService()

        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="元のテキスト",
            normalized_text="前回MTGの議事内容です。進捗確認を行いました。",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        slack_messages = [
            SlackMessageData(
                ts="1234567890.123456",
                user_name="田中太郎",
                text="次回のMTGでデザインレビューをお願いします",
                posted_at=datetime.now(),
            ),
        ]

        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="田中太郎",
                description="プロダクトマネージャー",
                created_at=datetime.now(),
                updated_at=None,
            ),
        ]

        input_data = AgendaGenerationInput(
            latest_note=note,
            slack_messages=slack_messages,
            dictionary=dictionary,
        )

        # Act
        prompt = service._build_prompt(input_data)

        # Assert
        assert "ユビキタス言語辞書" in prompt
        assert "田中太郎" in prompt
        assert "前回MTGの議事録" in prompt
        assert "進捗確認を行いました" in prompt
        assert "Slack履歴" in prompt
        assert "デザインレビュー" in prompt
        assert "前回議事録とSlack履歴の両方を参照しています" in prompt

    def test_build_prompt_with_note_only(self) -> None:
        """議事録のみの場合のプロンプト構築"""
        # Arrange
        service = AgendaGenerationService()

        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="元のテキスト",
            normalized_text="前回MTGの議事内容です。",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        input_data = AgendaGenerationInput(
            latest_note=note,
            slack_messages=[],
            dictionary=[],
        )

        # Act
        prompt = service._build_prompt(input_data)

        # Assert
        assert "前回MTGの議事録" in prompt
        assert "前回議事録のみを参照しています（Slack履歴なし）" in prompt
        assert "Slack履歴" not in prompt or "Slack履歴なし" in prompt

    def test_build_prompt_with_slack_only(self) -> None:
        """Slack履歴のみの場合のプロンプト構築"""
        # Arrange
        service = AgendaGenerationService()

        slack_messages = [
            SlackMessageData(
                ts="1234567890.123456",
                user_name="田中太郎",
                text="新機能について議論したい",
                posted_at=datetime.now(),
            ),
        ]

        input_data = AgendaGenerationInput(
            latest_note=None,
            slack_messages=slack_messages,
            dictionary=[],
        )

        # Act
        prompt = service._build_prompt(input_data)

        # Assert
        assert "Slack履歴のみを参照しています（前回議事録なし）" in prompt
        assert "新機能について議論したい" in prompt

    def test_build_prompt_with_no_data(self) -> None:
        """データなしの場合のプロンプト構築"""
        # Arrange
        service = AgendaGenerationService()

        input_data = AgendaGenerationInput(
            latest_note=None,
            slack_messages=[],
            dictionary=[],
        )

        # Act
        prompt = service._build_prompt(input_data)

        # Assert
        assert "参照できる情報がありません" in prompt
        assert "一般的なアジェンダ形式で生成してください" in prompt

    def test_build_prompt_limits_slack_messages_to_50(self) -> None:
        """Slackメッセージが50件に制限されることを確認"""
        # Arrange
        service = AgendaGenerationService()

        slack_messages = [
            SlackMessageData(
                ts=f"123456789{i}.123456",
                user_name=f"User{i}",
                text=f"メッセージ{i}",
                posted_at=datetime.now(),
            )
            for i in range(100)
        ]

        input_data = AgendaGenerationInput(
            latest_note=None,
            slack_messages=slack_messages,
            dictionary=[],
        )

        # Act
        prompt = service._build_prompt(input_data)

        # Assert
        # 50件目は含まれる
        assert "メッセージ49" in prompt
        # 51件目以降は含まれない
        assert "メッセージ50" not in prompt


class TestAgendaGenerationServiceGenerate:
    """Test AgendaGenerationService.generate method."""

    @pytest.mark.skip(reason="Requires mocking invoke_claude")
    async def test_generate_returns_llm_response(self) -> None:
        """生成メソッドがLLMレスポンスを返す"""
        # This test requires mocking invoke_claude
        pass

    @pytest.mark.skip(reason="Requires mocking invoke_claude")
    async def test_generate_raises_on_llm_failure(self) -> None:
        """LLM呼び出し失敗時に例外が発生する"""
        # This test requires mocking invoke_claude
        pass
