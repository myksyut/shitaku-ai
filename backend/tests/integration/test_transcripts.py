# Transcript Integration Test - Design Doc: transcript-management-design.md
# Generated: 2026-02-02 | Quota: 4/3 integration (exceeds by 1 for CRUD coverage)
"""
Transcript管理機能の統合テスト

テスト対象: Transcript API
- トランスクリプト作成（POST /transcripts）
- トランスクリプト一覧取得（GET /transcripts）
- トランスクリプト詳細取得（GET /transcripts/{id}）
- トランスクリプト削除（DELETE /transcripts/{id}）
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptEntry,
    TranscriptStructuredData,
)
from src.main import app
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.api.v1.endpoints.transcripts import get_repository

# テスト用の固定UUID
TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_RECURRING_MEETING_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_TRANSCRIPT_ID = UUID("33333333-3333-3333-3333-333333333333")


def override_get_current_user_id() -> UUID:
    """認証をモック化するためのオーバーライド関数."""
    return TEST_USER_ID


@pytest.fixture
def authenticated_client() -> Generator[TestClient, None, None]:
    """認証済みテストクライアントを作成."""
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_repository() -> MagicMock:
    """MeetingTranscriptRepositoryをモック化."""
    mock_repo = MagicMock()
    mock_repo.create = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.get_by_recurring_meeting = AsyncMock(return_value=[])
    mock_repo.delete = AsyncMock(return_value=False)
    return mock_repo


@pytest.fixture
def sample_transcript() -> MeetingTranscript:
    """サンプルトランスクリプトを作成."""
    return MeetingTranscript(
        id=TEST_TRANSCRIPT_ID,
        recurring_meeting_id=TEST_RECURRING_MEETING_ID,
        meeting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        google_doc_id="doc_123abc",
        raw_text="田中: こんにちは\n佐藤: お疲れ様です",
        structured_data=TranscriptStructuredData(
            entries=[
                TranscriptEntry(speaker="田中", timestamp="10:00", text="こんにちは"),
                TranscriptEntry(speaker="佐藤", timestamp="10:01", text="お疲れ様です"),
            ]
        ),
        match_confidence=0.85,
        created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def mock_repository_with_transcript(mock_repository: MagicMock, sample_transcript: MeetingTranscript) -> MagicMock:
    """既存のトランスクリプトがあるリポジトリをモック化."""
    mock_repository.get_by_id = AsyncMock(return_value=sample_transcript)
    mock_repository.get_by_recurring_meeting = AsyncMock(return_value=[sample_transcript])
    mock_repository.delete = AsyncMock(return_value=True)
    return mock_repository


class TestTranscriptIntegration:
    """Transcript APIの統合テスト"""

    # AC: "When ユーザーがトランスクリプトを作成すると、
    #      システムはトランスクリプトを保存し201を返す"
    # ROI: 48/10 = 4.8 | ビジネス価値: 8 | 頻度: 6
    # 振る舞い: 作成リクエスト -> バリデーション -> DB保存 -> 201レスポンス
    # @category: core-functionality
    # @dependency: MeetingTranscriptRepository
    # @complexity: medium
    #
    # 検証項目:
    # - 有効なリクエストで201が返却される
    # - レスポンスにid, is_auto_linked, needs_manual_confirmationが含まれる
    # - match_confidence >= 0.7 の場合 is_auto_linked=True
    def test_create_transcript_successfully(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
        sample_transcript: MeetingTranscript,
    ) -> None:
        """AC1: トランスクリプト作成で201を返す"""
        # Arrange: リポジトリをモックに差し替え
        mock_repository.create = AsyncMock(return_value=sample_transcript)
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: POST /api/v1/transcripts
            request_data = {
                "recurring_meeting_id": str(TEST_RECURRING_MEETING_ID),
                "meeting_date": "2024-01-15T10:00:00Z",
                "google_doc_id": "doc_123abc",
                "raw_text": "田中: こんにちは\n佐藤: お疲れ様です",
                "structured_data": {
                    "entries": [
                        {"speaker": "田中", "timestamp": "10:00", "text": "こんにちは"},
                        {"speaker": "佐藤", "timestamp": "10:01", "text": "お疲れ様です"},
                    ]
                },
                "match_confidence": 0.85,
            }
            response = authenticated_client.post("/api/v1/transcripts", json=request_data)

            # Assert: 201レスポンス
            assert response.status_code == 201

            # Assert: レスポンスに必須フィールドが含まれる
            data = response.json()
            assert "id" in data
            assert data["recurring_meeting_id"] == str(TEST_RECURRING_MEETING_ID)
            assert data["google_doc_id"] == "doc_123abc"
            assert data["match_confidence"] == 0.85

            # Assert: is_auto_linked/needs_manual_confirmation が正しく計算される
            assert data["is_auto_linked"] is True  # match_confidence >= 0.7
            assert data["needs_manual_confirmation"] is False

            # Assert: リポジトリのcreateが呼び出されている
            mock_repository.create.assert_called_once()
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーが定例MTGのトランスクリプト一覧を要求すると、
    #      システムは該当定例MTGのトランスクリプト一覧を返す"
    # ROI: 42/9 = 4.7 | ビジネス価値: 7 | 頻度: 7
    # 振る舞い: 一覧要求 -> recurring_meeting_idフィルタ -> DB検索 -> 一覧返却
    # @category: core-functionality
    # @dependency: MeetingTranscriptRepository
    # @complexity: low
    #
    # 検証項目:
    # - 認証済みユーザーの定例MTGのトランスクリプトのみが返却される
    # - トランスクリプトがない場合は空配列が返却される
    def test_get_transcripts_returns_list(
        self,
        authenticated_client: TestClient,
        mock_repository_with_transcript: MagicMock,
    ) -> None:
        """AC2: 定例MTGのトランスクリプト一覧を取得"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_transcript

        try:
            # Act: GET /api/v1/transcripts?recurring_meeting_id=xxx
            response = authenticated_client.get(f"/api/v1/transcripts?recurring_meeting_id={TEST_RECURRING_MEETING_ID}")

            # Assert: 200レスポンス
            assert response.status_code == 200

            # Assert: 認証ユーザーのトランスクリプトのみが返却される
            data = response.json()
            assert len(data) == 1
            transcript = data[0]

            # Assert: 各トランスクリプトに必須フィールドが含まれる
            assert transcript["id"] == str(TEST_TRANSCRIPT_ID)
            assert transcript["recurring_meeting_id"] == str(TEST_RECURRING_MEETING_ID)
            assert transcript["google_doc_id"] == "doc_123abc"
            assert "structured_data" in transcript
            assert "created_at" in transcript

            # Assert: リポジトリがrecurring_meeting_idで呼び出されている
            mock_repository_with_transcript.get_by_recurring_meeting.assert_called_once_with(
                TEST_RECURRING_MEETING_ID, None
            )
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_get_transcripts_returns_empty_when_no_transcripts(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
    ) -> None:
        """トランスクリプトがない場合は空配列が返却される"""
        # Arrange: 空のリポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: GET /api/v1/transcripts?recurring_meeting_id=xxx
            response = authenticated_client.get(f"/api/v1/transcripts?recurring_meeting_id={TEST_RECURRING_MEETING_ID}")

            # Assert: 200レスポンスで空配列
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーがトランスクリプト詳細を要求すると、
    #      システムは該当トランスクリプトを返す"
    # ROI: 30/8 = 3.75 | ビジネス価値: 6 | 頻度: 5
    # 振る舞い: 詳細要求 -> ID検索 -> トランスクリプト返却 or 404
    # @category: core-functionality
    # @dependency: MeetingTranscriptRepository
    # @complexity: low
    #
    # 検証項目:
    # - 存在するトランスクリプトで200が返却される
    # - 存在しないトランスクリプトで404が返却される
    def test_get_transcript_by_id(
        self,
        authenticated_client: TestClient,
        mock_repository_with_transcript: MagicMock,
    ) -> None:
        """AC3: トランスクリプト詳細を取得"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_transcript

        try:
            # Act: GET /api/v1/transcripts/{transcript_id}
            response = authenticated_client.get(f"/api/v1/transcripts/{TEST_TRANSCRIPT_ID}")

            # Assert: 200レスポンス
            assert response.status_code == 200

            # Assert: トランスクリプト詳細が返却される
            data = response.json()
            assert data["id"] == str(TEST_TRANSCRIPT_ID)
            assert data["recurring_meeting_id"] == str(TEST_RECURRING_MEETING_ID)
            assert data["google_doc_id"] == "doc_123abc"
            assert data["raw_text"] == "田中: こんにちは\n佐藤: お疲れ様です"

            # Assert: 構造化データが含まれる
            assert data["structured_data"] is not None
            assert len(data["structured_data"]["entries"]) == 2

            # Assert: リポジトリがIDで呼び出されている
            mock_repository_with_transcript.get_by_id.assert_called_once_with(TEST_TRANSCRIPT_ID)
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_get_transcript_returns_404_when_not_found(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
    ) -> None:
        """存在しないトランスクリプトで404が返却される"""
        # Arrange: トランスクリプトが見つからないリポジトリ
        mock_repository.get_by_id = AsyncMock(return_value=None)
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: GET /api/v1/transcripts/{transcript_id}
            non_existent_id = uuid4()
            response = authenticated_client.get(f"/api/v1/transcripts/{non_existent_id}")

            # Assert: 404レスポンス
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーがトランスクリプトを削除すると、
    #      システムは該当トランスクリプトを削除し204を返す"
    # ROI: 24/6 = 4.0 | ビジネス価値: 5 | 頻度: 3
    # 振る舞い: 削除要求 -> ID検索 -> DB削除 -> 204返却
    # @category: core-functionality
    # @dependency: MeetingTranscriptRepository
    # @complexity: low
    #
    # 検証項目:
    # - 存在するトランスクリプトの削除で204が返却される
    # - 存在しないトランスクリプトの削除で404が返却される
    def test_delete_transcript_removes_transcript(
        self,
        authenticated_client: TestClient,
        mock_repository_with_transcript: MagicMock,
    ) -> None:
        """AC4: トランスクリプト削除で204を返す"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_transcript

        try:
            # Act: DELETE /api/v1/transcripts/{transcript_id}
            response = authenticated_client.delete(f"/api/v1/transcripts/{TEST_TRANSCRIPT_ID}")

            # Assert: 204レスポンス
            assert response.status_code == 204

            # Assert: リポジトリのdeleteが正しく呼び出されている
            mock_repository_with_transcript.delete.assert_called_once_with(TEST_TRANSCRIPT_ID)
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_delete_transcript_returns_404_when_not_found(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
    ) -> None:
        """存在しないトランスクリプト削除で404が返却される"""
        # Arrange: 削除がFalseを返すリポジトリ
        mock_repository.delete = AsyncMock(return_value=False)
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: DELETE /api/v1/transcripts/{transcript_id}
            non_existent_id = uuid4()
            response = authenticated_client.delete(f"/api/v1/transcripts/{non_existent_id}")

            # Assert: 404レスポンス
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_repository, None)
