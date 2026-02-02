"""GoogleDocsClient tests with mocked HTTP responses."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.external.google_docs_client import (
    DocsDocument,
    GoogleDocsClient,
)


class TestGoogleDocsClient:
    """GoogleDocsClientのテスト"""

    @pytest.fixture
    def client(self) -> GoogleDocsClient:
        """GoogleDocsClientインスタンスを返す"""
        return GoogleDocsClient(access_token="test_access_token")

    def test_init_without_token(self) -> None:
        """access_tokenなしで初期化するとエラーになる"""
        with pytest.raises(ValueError, match="access_token is required"):
            GoogleDocsClient(access_token="")

    @pytest.mark.asyncio
    async def test_get_document_content_success(self, client: GoogleDocsClient) -> None:
        """ドキュメントコンテンツを正しく取得できる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documentId": "doc_001",
            "title": "定例会議 2024-01-15",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "田中 (10:00)\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "おはようございます。\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "鈴木 (10:01)\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "おはようございます。\n"}},
                            ]
                        }
                    },
                ]
            },
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            doc = await client.get_document_content("doc_001")

        # Assert
        assert doc is not None
        assert doc.document_id == "doc_001"
        assert doc.title == "定例会議 2024-01-15"
        assert "田中 (10:00)" in doc.body_text
        assert "おはようございます。" in doc.body_text
        assert "鈴木 (10:01)" in doc.body_text

    @pytest.mark.asyncio
    async def test_get_document_content_not_found(self, client: GoogleDocsClient) -> None:
        """ドキュメントが見つからない場合はNoneを返す"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            doc = await client.get_document_content("nonexistent")

        # Assert
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_document_content_api_error(self, client: GoogleDocsClient) -> None:
        """APIエラー時に例外を発生させる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"message": "The caller does not have permission"}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ValueError, match="Google Docs API error"),
        ):
            await client.get_document_content("doc_001")

    @pytest.mark.asyncio
    async def test_get_document_text_success(self, client: GoogleDocsClient) -> None:
        """テキストコンテンツのみを取得できる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documentId": "doc_001",
            "title": "定例会議",
            "body": {"content": [{"paragraph": {"elements": [{"textRun": {"content": "テストテキスト\n"}}]}}]},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            text = await client.get_document_text("doc_001")

        # Assert
        assert text is not None
        assert "テストテキスト" in text

    @pytest.mark.asyncio
    async def test_get_document_text_not_found(self, client: GoogleDocsClient) -> None:
        """ドキュメントが見つからない場合はNoneを返す"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            text = await client.get_document_text("nonexistent")

        # Assert
        assert text is None


class TestExtractText:
    """テキスト抽出のテスト"""

    @pytest.fixture
    def client(self) -> GoogleDocsClient:
        """GoogleDocsClientインスタンスを返す"""
        return GoogleDocsClient(access_token="test_access_token")

    def test_extract_text_from_simple_paragraph(self, client: GoogleDocsClient) -> None:
        """シンプルな段落からテキストを抽出できる"""
        body = {"content": [{"paragraph": {"elements": [{"textRun": {"content": "Hello, World!\n"}}]}}]}

        text = client._extract_text_from_body(body)

        assert text == "Hello, World!\n"

    def test_extract_text_from_multiple_paragraphs(self, client: GoogleDocsClient) -> None:
        """複数の段落からテキストを抽出できる"""
        body = {
            "content": [
                {"paragraph": {"elements": [{"textRun": {"content": "First line\n"}}]}},
                {"paragraph": {"elements": [{"textRun": {"content": "Second line\n"}}]}},
            ]
        }

        text = client._extract_text_from_body(body)

        assert text == "First line\nSecond line\n"

    def test_extract_text_from_table(self, client: GoogleDocsClient) -> None:
        """テーブルからテキストを抽出できる"""
        body = {
            "content": [
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {"content": [{"paragraph": {"elements": [{"textRun": {"content": "Cell 1\n"}}]}}]},
                                    {"content": [{"paragraph": {"elements": [{"textRun": {"content": "Cell 2\n"}}]}}]},
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        text = client._extract_text_from_body(body)

        assert "Cell 1" in text
        assert "Cell 2" in text

    def test_extract_text_from_empty_body(self, client: GoogleDocsClient) -> None:
        """空のボディからは空文字列を返す"""
        body: dict[str, list[str]] = {"content": []}

        text = client._extract_text_from_body(body)

        assert text == ""

    def test_extract_text_from_invalid_body(self, client: GoogleDocsClient) -> None:
        """無効なボディからは空文字列を返す"""
        text = client._extract_text_from_body(None)
        assert text == ""

        text = client._extract_text_from_body("invalid")
        assert text == ""


class TestDocsDocument:
    """DocsDocumentデータクラスのテスト"""

    def test_docs_document_creation(self) -> None:
        """DocsDocumentが正しく作成できる"""
        doc = DocsDocument(
            document_id="doc_001",
            title="定例会議 2024-01-15",
            body_text="田中: おはようございます。",
        )

        assert doc.document_id == "doc_001"
        assert doc.title == "定例会議 2024-01-15"
        assert doc.body_text == "田中: おはようございます。"

    def test_docs_document_with_empty_body(self) -> None:
        """空のボディでも作成できる"""
        doc = DocsDocument(
            document_id="doc_001",
            title="空のドキュメント",
            body_text="",
        )

        assert doc.body_text == ""
