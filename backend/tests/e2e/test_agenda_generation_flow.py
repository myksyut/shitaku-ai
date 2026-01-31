# Complete Agenda Generation Flow E2E Test - Design Doc: mvp-core-features.md
# Generated: 2026-01-31 | Quota: 1/2 E2E
# Test Type: End-to-End Test
# Implementation Timing: After all features are fully implemented
"""
完全なアジェンダ生成フローのE2Eテスト

クリティカルユーザージャーニー:
エージェント作成 -> 辞書登録 -> 議事録アップロード -> Slack連携 -> アジェンダ生成

このテストは全機能の実装完了後に実行します。
モック禁止 - 実際のDB、LLM API、Slack APIを使用（テスト環境）
"""

import pytest
from fastapi.testclient import TestClient


class TestAgendaGenerationFlowE2E:
    """完全なアジェンダ生成フローのE2Eテスト"""

    # ユーザージャーニー:
    # エージェント作成 -> 辞書登録 -> 議事録アップロード -> Slack連携 -> アジェンダ生成
    # ROI: 110/38 = 2.9 | ビジネス価値: 10 | 頻度: 10 | 法的: false
    # 振る舞い:
    #   1. ユーザーがログイン
    #   2. MTGエージェントを作成
    #   3. ユビキタス言語辞書に人名・プロジェクト名を登録
    #   4. 議事録テキストをアップロード（正規化される）
    #   5. Slack連携を設定（OAuth完了）
    #   6. アジェンダ生成ボタンをクリック
    #   7. 生成されたアジェンダをプレビュー表示
    #   8. アジェンダを保存
    # @category: e2e
    # @dependency: full-system
    # @complexity: high
    #
    # 検証項目:
    # - 全ステップが正常に完了する
    # - 各ステップでデータが正しく永続化される
    # - 正規化処理で辞書の表記揺れが適用される
    # - アジェンダに前回議事録とSlack履歴の内容が反映される
    # - 30秒以内にアジェンダが生成される
    @pytest.mark.skip(reason="E2E test - Run after all features are implemented")
    def test_complete_agenda_generation_user_journey(self, test_client: TestClient) -> None:
        """ユーザージャーニー: 閲覧から確認メールまでのアジェンダ生成完了"""
        # ============================================================
        # Step 1: ユーザー認証
        # ============================================================
        # Arrange:
        # - テストユーザーを準備（Supabase Auth）
        # - ログインしてJWTトークンを取得

        # Act:
        # - POST /api/v1/auth/login

        # Assert:
        # - 認証成功、JWTトークン取得

        # ============================================================
        # Step 2: MTGエージェント作成
        # ============================================================
        # Arrange:
        # - 認証ヘッダーを設定

        # Act:
        # - POST /api/v1/agents
        #   body: {name: "週次定例MTG", description: "チームAの週次定例"}

        # Assert:
        # - 201レスポンス
        # - agent_idを取得

        # ============================================================
        # Step 3: ユビキタス言語辞書に人名・プロジェクト名を登録
        # ============================================================
        # Act:
        # - POST /api/v1/dictionary
        #   body: {canonical_name: "金沢太郎", category: "person", variants: ["かなざわ", "金澤"]}
        # - POST /api/v1/dictionary
        #   body: {canonical_name: "Shitaku.ai", category: "project", variants: ["支度", "したく"]}

        # Assert:
        # - 各エントリが201レスポンス
        # - 辞書一覧に2件追加

        # ============================================================
        # Step 4: 議事録テキストをアップロード（正規化される）
        # ============================================================
        # Arrange:
        # - 表記揺れを含む議事録テキストを準備
        #   例: "かなざわさんが支度プロジェクトの進捗を報告しました"

        # Act:
        # - POST /api/v1/meeting-notes
        #   body: {agent_id, text, meeting_date}

        # Assert:
        # - 201レスポンス
        # - normalized_textに"金沢太郎"と"Shitaku.ai"が含まれる
        # - meeting_note_idを取得

        # ============================================================
        # Step 5: Slack連携を設定
        # ============================================================
        # Note: 実E2Eテストでは実際のSlack OAuth完了が必要
        # テスト環境ではテスト用のSlack連携データを事前に準備

        # Act:
        # - GET /api/v1/slack/auth (OAuth開始)
        # - [外部] Slack OAuth完了
        # - GET /api/v1/slack/callback?code=xxx&state=yyy
        # - PUT /api/v1/agents/{agent_id}
        #   body: {slack_channel_id: "C12345"}

        # Assert:
        # - Slack連携が保存されている
        # - エージェントにチャンネルが紐付いている

        # ============================================================
        # Step 6: アジェンダ生成
        # ============================================================
        # Act:
        # - POST /api/v1/agendas/generate
        #   body: {agent_id}

        # Assert:
        # - 200/201レスポンス
        # - レスポンス時間 <= 30秒
        # - contentが空でない
        # - contentに前回議事録の内容が反映されている

        # ============================================================
        # Step 7: アジェンダ保存
        # ============================================================
        # Act:
        # - 生成されたアジェンダを編集（任意）
        # - PUT /api/v1/agendas/{agenda_id}
        #   body: {content: "編集後のアジェンダ"}

        # Assert:
        # - 200レスポンス
        # - DBに編集内容が保存されている

        # ============================================================
        # 最終検証
        # ============================================================
        # Assert:
        # - 全データが正しく連携している
        # - agents, dictionary_entries, meeting_notes, agendas に各1件以上
        # - source_note_idが正しくリンクされている
        pass

    # ユーザージャーニー: 辞書作成 -> 議事録アップロード -> 正規化結果確認
    # ROI: 89/38 = 2.3 | ビジネス価値: 10 | 頻度: 8
    # 振る舞い:
    #   1. ユーザーがログイン
    #   2. ユビキタス言語辞書にエントリを登録
    #   3. 議事録テキストをアップロード
    #   4. 正規化前後のテキストを比較
    # @category: e2e
    # @dependency: full-system
    # @complexity: medium
    #
    # 検証項目:
    # - 辞書エントリの表記揺れが正規化に適用される
    # - 正規化前後の差分が視覚的に確認できる
    # - 複数の表記揺れパターンが正しく置換される
    @pytest.mark.skip(reason="E2E test - Run after all features are implemented")
    def test_dictionary_driven_normalization_flow(self, test_client: TestClient) -> None:
        """ユーザージャーニー: 辞書駆動の正規化フロー"""
        # ============================================================
        # Step 1: ユーザー認証
        # ============================================================
        # (Step 1 same as above)

        # ============================================================
        # Step 2: ユビキタス言語辞書にエントリを登録
        # ============================================================
        # Act:
        # - POST /api/v1/dictionary
        #   body: {
        #     canonical_name: "田中花子",
        #     category: "person",
        #     variants: ["たなか", "タナカ", "Tanaka"]
        #   }

        # Assert:
        # - 201レスポンス

        # ============================================================
        # Step 3: エージェント作成
        # ============================================================
        # Act:
        # - POST /api/v1/agents
        #   body: {name: "テストMTG"}

        # Assert:
        # - 201レスポンス

        # ============================================================
        # Step 4: 議事録テキストをアップロード
        # ============================================================
        # Arrange:
        # - 複数の表記揺れを含むテキストを準備
        #   例: "たなかさんとTanakaさんが参加。タナカの報告を確認"

        # Act:
        # - POST /api/v1/meeting-notes
        #   body: {agent_id, text, meeting_date}

        # Assert:
        # - 201レスポンス
        # - normalized_textに全て"田中花子"として正規化されている
        # - original_textは変更されていない

        # ============================================================
        # Step 5: 正規化結果確認
        # ============================================================
        # Act:
        # - GET /api/v1/meeting-notes/{meeting_note_id}

        # Assert:
        # - original_text != normalized_text
        # - normalized_textに"田中花子"が3回含まれる
        # - "たなか", "Tanaka", "タナカ" がnormalized_textに含まれていない
        pass
