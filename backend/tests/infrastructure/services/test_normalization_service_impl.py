"""Tests for NormalizationServiceImpl."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.services.normalization_service import NormalizationError
from src.infrastructure.services.normalization_service_impl import NormalizationServiceImpl


class TestNormalizationServiceImpl:
    """NormalizationServiceImplのテスト."""

    def test_normalize_with_empty_dictionary(self) -> None:
        """辞書が空の場合は正規化しないこと."""
        service = NormalizationServiceImpl()
        text = "テストテキスト"

        result = service.normalize(text, [])

        assert result.original_text == text
        assert result.normalized_text == text
        assert result.replacements == []
        assert result.replacement_count == 0

    @patch("src.infrastructure.services.normalization_service_impl.invoke_claude")
    def test_normalize_with_valid_response(self, mock_invoke_claude: MagicMock) -> None:
        """正常なLLMレスポンスを処理できること."""
        # モックレスポンスを設定
        mock_invoke_claude.return_value = """{
  "normalized_text": "金沢太郎さんが発言しました",
  "replacements": [
    {"original": "かなざわ", "canonical": "金沢太郎", "start_pos": 0, "end_pos": 4}
  ]
}"""

        service = NormalizationServiceImpl()
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="金沢太郎",
                description="フロントエンド担当",
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        result = service.normalize("かなざわさんが発言しました", dictionary)

        assert result.normalized_text == "金沢太郎さんが発言しました"
        assert result.replacement_count == 1
        assert result.replacements[0].original == "かなざわ"
        assert result.replacements[0].canonical == "金沢太郎"

    @patch("src.infrastructure.services.normalization_service_impl.invoke_claude")
    def test_normalize_with_json_code_block(self, mock_invoke_claude: MagicMock) -> None:
        """JSONがコードブロックで囲まれている場合も処理できること."""
        mock_invoke_claude.return_value = """```json
{
  "normalized_text": "正規化後のテキスト",
  "replacements": []
}
```"""

        service = NormalizationServiceImpl()
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="テスト",
                description=None,
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        result = service.normalize("テスト", dictionary)

        assert result.normalized_text == "正規化後のテキスト"

    @patch("src.infrastructure.services.normalization_service_impl.invoke_claude")
    def test_normalize_with_llm_returning_none(self, mock_invoke_claude: MagicMock) -> None:
        """LLMがNoneを返した場合はエラーになること."""
        mock_invoke_claude.return_value = None

        service = NormalizationServiceImpl()
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="テスト",
                description=None,
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        with pytest.raises(NormalizationError) as exc_info:
            service.normalize("テスト", dictionary)

        assert "LLM API returned None" in str(exc_info.value)

    @patch("src.infrastructure.services.normalization_service_impl.invoke_claude")
    def test_normalize_with_invalid_json_response(self, mock_invoke_claude: MagicMock) -> None:
        """不正なJSONレスポンスの場合は元テキストを返すこと（フォールバック）."""
        mock_invoke_claude.return_value = "これは有効なJSONではありません"

        service = NormalizationServiceImpl()
        original_text = "かなざわさんが発言しました"
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="金沢太郎",
                description=None,
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        result = service.normalize(original_text, dictionary)

        # フォールバック: 元テキストがそのまま返される
        assert result.original_text == original_text
        assert result.normalized_text == original_text
        assert result.replacements == []

    @patch("src.infrastructure.services.normalization_service_impl.invoke_claude")
    def test_normalize_with_exception(self, mock_invoke_claude: MagicMock) -> None:
        """LLM呼び出しで例外が発生した場合はNormalizationErrorになること."""
        mock_invoke_claude.side_effect = Exception("Network error")

        service = NormalizationServiceImpl()
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="テスト",
                description=None,
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        with pytest.raises(NormalizationError) as exc_info:
            service.normalize("テスト", dictionary)

        assert "Normalization failed" in str(exc_info.value)

    def test_build_prompt_format(self) -> None:
        """プロンプトが正しいフォーマットで生成されること."""
        service = NormalizationServiceImpl()
        dictionary = [
            DictionaryEntry(
                id=uuid4(),
                user_id=uuid4(),
                canonical_name="金沢太郎",
                description="フロントエンド担当",
                created_at=datetime.now(),
                updated_at=None,
            )
        ]

        prompt = service._build_prompt("テストテキスト", dictionary)

        assert "金沢太郎" in prompt
        assert "フロントエンド担当" in prompt
        assert "テストテキスト" in prompt
        assert "normalized_text" in prompt
        assert "replacements" in prompt
