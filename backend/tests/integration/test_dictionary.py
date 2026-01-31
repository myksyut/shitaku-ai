# Ubiquitous Language Dictionary Integration Test - Design Doc: mvp-core-features.md
# Generated: 2026-01-31 | Quota: 3/3 integration, 0/2 E2E
"""
ユビキタス言語辞書機能の統合テスト

テスト対象: F2 ユビキタス言語辞書
- 辞書エントリCRUD操作のAPI連携
- カテゴリフィルタリング機能
- 重複チェックのバリデーション
"""

import pytest
from fastapi.testclient import TestClient


class TestDictionaryIntegration:
    """ユビキタス言語辞書の統合テスト"""

    # AC: "When ユーザーが辞書エントリ作成フォームに正式名称・カテゴリ・表記揺れを
    #      入力して保存すると、システムはエントリをDBに保存する"
    # Property: `dictionary_entries.count == previous_count + 1`
    # ROI: 88/11 = 8.0 | ビジネス価値: 10 | 頻度: 8
    # 振る舞い: 正式名称・カテゴリ・表記揺れ入力 -> API呼び出し -> DB保存
    # @category: core-functionality
    # @dependency: DictionaryEntryRepository, DictionaryVariantRepository, Supabase
    # @complexity: medium
    #
    # 検証項目:
    # - 正常レスポンス(201)が返却される
    # - レスポンスにid, canonical_name, category, variantsが含まれる
    # - DBにエントリが永続化されている
    # - DBにvariantsが永続化されている
    @pytest.mark.skip(reason="Not implemented yet")
    def test_create_dictionary_entry_with_variants(self, authenticated_client: TestClient) -> None:
        """AC1: 辞書エントリ作成で正式名称・カテゴリ・表記揺れがDBに保存される"""
        # Arrange:
        # - 認証済みユーザーを準備（authenticated_client fixture）
        # - 作成前のエントリ数を取得

        # Act:
        # - POST /api/v1/dictionary で辞書エントリ作成
        #   body: {canonical_name, category, description, variants}

        # Assert:
        # - 作成レスポンスが201
        # - レスポンスにid, canonical_name, category, variantsが含まれる
        # - Property: dictionary_entries.count == previous_count + 1
        pass

    # AC: "When ユーザーが辞書一覧画面でカテゴリフィルタを選択すると、
    #      システムは該当カテゴリのエントリのみを表示する"
    # Property: `displayed.every(entry => entry.category == selected_category)`
    # ROI: 56/11 = 5.1 | ビジネス価値: 7 | 頻度: 7
    # 振る舞い: カテゴリフィルタ選択 -> API呼び出し(query param) -> フィルタ結果返却
    # @category: core-functionality
    # @dependency: DictionaryEntryRepository, Supabase
    # @complexity: low
    #
    # 検証項目:
    # - レスポンスの全エントリが指定カテゴリに一致
    # - 他カテゴリのエントリが含まれていない
    @pytest.mark.skip(reason="Not implemented yet")
    def test_filter_dictionary_by_category(self, authenticated_client: TestClient) -> None:
        """AC2: カテゴリフィルタで該当カテゴリのエントリのみが返却される"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - 異なるカテゴリで複数の辞書エントリを作成
        #   例: person, project, term

        # Act:
        # - GET /api/v1/dictionary?category=person でフィルタ取得

        # Assert:
        # - Property: displayed.every(entry => entry.category == "person")
        # - 他カテゴリのエントリが含まれていない
        pass

    # AC: "If 正式名称が既存エントリと重複する場合、
    #      then システムはエラーメッセージを表示する"
    # ROI: 32/11 = 2.9 | ビジネス価値: 6 | 頻度: 4
    # 振る舞い: 重複する正式名称入力 -> API呼び出し -> 409 Conflictエラー
    # @category: edge-case
    # @dependency: DictionaryEntryRepository, Supabase
    # @complexity: low
    #
    # 検証項目:
    # - 409 Conflictレスポンスが返却される
    # - エラーメッセージに重複の旨が含まれる
    # - DBにエントリが追加されていない
    @pytest.mark.skip(reason="Not implemented yet")
    def test_create_dictionary_entry_duplicate_name_error(
        self, authenticated_client: TestClient
    ) -> None:
        """AC5: 正式名称重複時にエラーレスポンスが返却される"""
        # Arrange:
        # - 認証済みユーザーを準備
        # - 辞書エントリを作成（canonical_name="テスト用語"）

        # Act:
        # - POST /api/v1/dictionary で同じcanonical_nameで再作成

        # Assert:
        # - 409 Conflictレスポンス
        # - エラーメッセージに重複の旨が含まれる
        pass
