"""GoogleDriveClient tests with mocked HTTP responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.external.google_drive_client import (
    DriveFile,
    GoogleDriveClient,
)


class TestGoogleDriveClient:
    """GoogleDriveClientのテスト"""

    @pytest.fixture
    def client(self) -> GoogleDriveClient:
        """GoogleDriveClientインスタンスを返す"""
        return GoogleDriveClient(access_token="test_access_token")

    def test_init_without_token(self) -> None:
        """access_tokenなしで初期化するとエラーになる"""
        with pytest.raises(ValueError, match="access_token is required"):
            GoogleDriveClient(access_token="")

    @pytest.mark.asyncio
    async def test_search_transcript_files_success(self, client: GoogleDriveClient) -> None:
        """Meet Recordingsフォルダからファイルを検索できる"""
        # Arrange
        mock_response_folder = MagicMock()
        mock_response_folder.status_code = 200
        mock_response_folder.json.return_value = {"files": [{"id": "folder_123", "name": "Meet Recordings"}]}

        mock_response_files = MagicMock()
        mock_response_files.status_code = 200
        mock_response_files.json.return_value = {
            "files": [
                {
                    "id": "doc_001",
                    "name": "定例会議 2024-01-15",
                    "mimeType": "application/vnd.google-apps.document",
                    "createdTime": "2024-01-15T10:00:00Z",
                    "modifiedTime": "2024-01-15T11:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc_001",
                },
                {
                    "id": "doc_002",
                    "name": "定例会議 2024-01-08",
                    "mimeType": "application/vnd.google-apps.document",
                    "createdTime": "2024-01-08T10:00:00Z",
                    "modifiedTime": "2024-01-08T11:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc_002",
                },
            ],
            "nextPageToken": None,
        }

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_response_folder, mock_response_files]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            files = await client.search_transcript_files()

        # Assert
        assert len(files) == 2
        assert files[0].id == "doc_001"
        assert files[0].name == "定例会議 2024-01-15"
        assert files[1].id == "doc_002"

    @pytest.mark.asyncio
    async def test_search_transcript_files_folder_not_found(self, client: GoogleDriveClient) -> None:
        """フォルダが見つからない場合は空リストを返す"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": []}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            files = await client.search_transcript_files()

        # Assert
        assert files == []

    @pytest.mark.asyncio
    async def test_search_transcript_files_api_error(self, client: GoogleDriveClient) -> None:
        """APIエラー時に例外を発生させる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid Credentials"}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ValueError, match="Google Drive API error"),
        ):
            await client.search_transcript_files()

    @pytest.mark.asyncio
    async def test_get_file_by_id_success(self, client: GoogleDriveClient) -> None:
        """ファイルIDでファイル情報を取得できる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "doc_001",
            "name": "定例会議 2024-01-15",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2024-01-15T10:00:00Z",
            "modifiedTime": "2024-01-15T11:00:00Z",
            "webViewLink": "https://docs.google.com/document/d/doc_001",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            file = await client.get_file_by_id("doc_001")

        # Assert
        assert file is not None
        assert file.id == "doc_001"
        assert file.name == "定例会議 2024-01-15"
        assert file.mime_type == "application/vnd.google-apps.document"

    @pytest.mark.asyncio
    async def test_get_file_by_id_not_found(self, client: GoogleDriveClient) -> None:
        """ファイルが見つからない場合はNoneを返す"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            file = await client.get_file_by_id("nonexistent")

        # Assert
        assert file is None

    @pytest.mark.asyncio
    async def test_get_file_by_id_api_error(self, client: GoogleDriveClient) -> None:
        """APIエラー時に例外を発生させる"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"message": "Insufficient Permission"}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ValueError, match="Google Drive API error"),
        ):
            await client.get_file_by_id("doc_001")


class TestDriveFile:
    """DriveFileデータクラスのテスト"""

    def test_drive_file_creation(self) -> None:
        """DriveFileが正しく作成できる"""
        created = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        modified = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        file = DriveFile(
            id="doc_001",
            name="定例会議 2024-01-15",
            mime_type="application/vnd.google-apps.document",
            created_time=created,
            modified_time=modified,
            web_view_link="https://docs.google.com/document/d/doc_001",
        )

        assert file.id == "doc_001"
        assert file.name == "定例会議 2024-01-15"
        assert file.mime_type == "application/vnd.google-apps.document"
        assert file.created_time == created
        assert file.modified_time == modified
        assert file.web_view_link == "https://docs.google.com/document/d/doc_001"

    def test_drive_file_without_web_view_link(self) -> None:
        """web_view_linkがNoneでも作成できる"""
        created = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        modified = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        file = DriveFile(
            id="doc_001",
            name="定例会議",
            mime_type="application/vnd.google-apps.document",
            created_time=created,
            modified_time=modified,
            web_view_link=None,
        )

        assert file.web_view_link is None
