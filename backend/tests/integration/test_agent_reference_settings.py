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

import pytest
from fastapi.testclient import TestClient


class TestAgentReferenceSettingsIntegration:
    """アジェンダ生成参照情報設定の統合テスト"""

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
    @pytest.mark.skip(reason="Not implemented yet")
    def test_collect_transcripts_from_multiple_recurring_meetings(self, authenticated_client: TestClient) -> None:
        """AC2-1/AC2-2: 複数定例MTGから設定件数分のトランスクリプトが日付降順で収集される"""
        # Arrange:
        # - 認証済みユーザーを準備（authenticated_client fixture）
        # - エージェントを作成（transcript_count: 3）
        # - 複数の定例MTGを作成しエージェントに紐付け
        # - 各定例にトランスクリプトを複数件作成
        # - RecurringMeetingRepositoryをモック化
        # - MeetingTranscriptRepositoryをモック化
        # - AgendaGenerationServiceをモック化（プロンプト内容を検証可能に）
        # - BedrockClientをモック化

        # Act:
        # - POST /api/v1/agendas/generate
        #   body: {agent_id}

        # Assert:
        # - 全定例からトランスクリプトが収集される
        # - 各定例からtranscript_count件数分が取得される
        # - トランスクリプトが日付降順でソートされている
        # - プロンプトにトランスクリプト情報が含まれる
        pass

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
    @pytest.mark.skip(reason="Not implemented yet")
    def test_prompt_includes_transcripts_with_meeting_info(self, authenticated_client: TestClient) -> None:
        """AC4-1: 収集したトランスクリプトが定例MTG情報付きでプロンプトに含まれる"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - エージェントを作成
        # - 定例MTGを作成しエージェントに紐付け
        # - トランスクリプトを作成
        # - AgendaGenerationService._build_promptの出力を検証可能にモック化
        # - BedrockClientをモック化

        # Act:
        # - POST /api/v1/agendas/generate
        #   body: {agent_id}

        # Assert:
        # - プロンプトにトランスクリプトセクションが存在する
        # - プロンプトに「複数の定例MTGからのトランスクリプト」であることが明示される
        # - 各トランスクリプトに定例MTG名と日付が含まれる
        # - アジェンダが正常に生成される
        pass

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
    @pytest.mark.skip(reason="Not implemented yet")
    def test_slack_messages_fetched_for_configured_days(self, authenticated_client: TestClient) -> None:
        """AC3-1: slack_message_daysで指定した日数分のSlackメッセージが取得される"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - エージェントを作成（slack_message_days: 14）
        # - Slack連携を設定
        # - SlackClientをモック化（呼び出しパラメータを検証可能に）
        # - BedrockClientをモック化

        # Act:
        # - POST /api/v1/agendas/generate
        #   body: {agent_id}

        # Assert:
        # - SlackClientが14日前からのメッセージを取得するパラメータで呼び出される
        # - oldest パラメータが (now - 14 days) のタイムスタンプである
        # - 取得したメッセージがプロンプトに含まれる
        pass
