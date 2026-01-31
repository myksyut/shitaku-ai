# Meeting Notes Integration Test - Design Doc: mvp-core-features.md
# Generated: 2026-01-31 | Quota: 2/3 integration, 0/2 E2E
"""
議事録アップロード + 正規化機能の統合テスト

テスト対象: F3 議事録アップロード + 正規化
- 議事録テキストのアップロードとDB保存
- ユビキタス言語辞書による正規化処理
- LLM APIエラー時のフォールバック処理
"""

import pytest
from fastapi.testclient import TestClient


class TestMeetingNotesIntegration:
    """議事録アップロード + 正規化の統合テスト"""

    # AC: "When ユーザーがエージェントを選択して議事録テキストをアップロードすると、
    #      システムは辞書を参照して固有名詞を正規化し、DBに保存する"
    # Property: `meeting_notes.count == previous_count + 1`
    # ROI: 99/11 = 9.0 | ビジネス価値: 10 | 頻度: 9
    # 振る舞い: エージェント選択+テキストアップロード -> 辞書参照 -> LLM正規化 -> DB保存
    # @category: core-functionality
    # @dependency: MeetingNoteRepository, DictionaryEntryRepository, BedrockClient, Supabase
    # @complexity: high
    #
    # 検証項目:
    # - 正常レスポンス(201)が返却される
    # - レスポンスにid, original_text, normalized_textが含まれる
    # - original_textは入力テキストと同一
    # - normalized_textは正規化処理の結果
    # - DBに議事録が永続化されている
    @pytest.mark.skip(reason="Not implemented yet")
    def test_upload_and_normalize_meeting_note(self, authenticated_client: TestClient) -> None:
        """AC1: 議事録アップロードで辞書参照正規化されDBに保存される"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - エージェントを作成
        # - 辞書エントリを作成（表記揺れを含む）
        #   例: canonical_name="金沢太郎", variants=["かなざわ", "金澤"]
        # - 表記揺れを含む議事録テキストを準備
        #   例: "かなざわさんが報告しました"
        # - 作成前の議事録数を取得
        # - BedrockClientをモック化（正規化結果を返す）

        # Act:
        # - POST /api/v1/meeting-notes でテキストアップロード
        #   body: {agent_id, text, meeting_date}

        # Assert:
        # - 作成レスポンスが201
        # - レスポンスにoriginal_text, normalized_textが含まれる
        # - normalized_textに"金沢太郎"が含まれる（正規化成功）
        # - Property: meeting_notes.count == previous_count + 1
        pass

    # AC: "If 正規化処理でLLM APIエラーが発生した場合、
    #      then システムは元テキストをそのまま保存し、ユーザーに警告を表示する"
    # ROI: 27/11 = 2.5 | ビジネス価値: 9 | 頻度: 2
    # 振る舞い: テキストアップロード -> LLM APIエラー -> 元テキスト保存 -> 警告返却
    # @category: edge-case
    # @dependency: MeetingNoteRepository, BedrockClient, Supabase
    # @complexity: medium
    #
    # 検証項目:
    # - レスポンスに警告メッセージが含まれる
    # - original_textとnormalized_textが同一（フォールバック）
    # - DBに議事録が永続化されている（元テキストのまま）
    @pytest.mark.skip(reason="Not implemented yet")
    def test_upload_meeting_note_llm_error_fallback(self, authenticated_client: TestClient) -> None:
        """AC3: LLM APIエラー時に元テキストが保存され警告が返却される"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - エージェントを作成
        # - BedrockClientをモック化（エラーを発生させる）

        # Act:
        # - POST /api/v1/meeting-notes でテキストアップロード

        # Assert:
        # - レスポンスに警告フラグまたはメッセージが含まれる
        # - original_text == normalized_text（フォールバック）
        # - DBに議事録が永続化されている
        pass
