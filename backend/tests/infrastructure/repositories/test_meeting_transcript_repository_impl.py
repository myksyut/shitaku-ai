"""MeetingTranscriptRepositoryImpl tests with mocked Supabase client."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptEntry,
    TranscriptStructuredData,
)
from src.infrastructure.repositories.meeting_transcript_repository_impl import (
    MeetingTranscriptRepositoryImpl,
)


class TestMeetingTranscriptRepositoryImpl:
    """MeetingTranscriptRepositoryImplのテスト"""

    @pytest.fixture
    def mock_supabase_client(self) -> MagicMock:
        """モック化されたSupabaseクライアントを返す"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_supabase_client: MagicMock) -> MeetingTranscriptRepositoryImpl:
        """リポジトリインスタンスを返す"""
        return MeetingTranscriptRepositoryImpl(client=mock_supabase_client)

    @pytest.fixture
    def sample_transcript(self) -> MeetingTranscript:
        """サンプルのMeetingTranscriptエンティティを返す"""
        return MeetingTranscript(
            id=uuid4(),
            recurring_meeting_id=uuid4(),
            meeting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            google_doc_id="doc_123456",
            raw_text="田中: おはようございます。\n鈴木: おはようございます。",
            structured_data=TranscriptStructuredData(
                entries=[
                    TranscriptEntry(speaker="田中", timestamp="10:00", text="おはようございます。"),
                    TranscriptEntry(speaker="鈴木", timestamp="10:01", text="おはようございます。"),
                ]
            ),
            match_confidence=0.85,
            created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
        sample_transcript: MeetingTranscript,
    ) -> None:
        """トランスクリプトを正しく作成できる"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = await repository.create(sample_transcript)

        # Assert
        assert result == sample_transcript
        mock_supabase_client.table.assert_called_once_with("meeting_transcripts")
        mock_table.insert.assert_called_once()
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["google_doc_id"] == "doc_123456"
        assert insert_data["match_confidence"] == 0.85
        assert insert_data["structured_data"]["entries"][0]["speaker"] == "田中"

    @pytest.mark.asyncio
    async def test_create_with_none_structured_data(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """structured_dataがNoneのトランスクリプトを作成できる"""
        # Arrange
        transcript = MeetingTranscript(
            id=uuid4(),
            recurring_meeting_id=uuid4(),
            meeting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            google_doc_id="doc_123456",
            raw_text="生テキストのみ",
            structured_data=None,
            match_confidence=0.5,
            created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = await repository.create(transcript)

        # Assert
        assert result == transcript
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["structured_data"] is None

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """IDでトランスクリプトを正しく取得できる"""
        # Arrange
        transcript_id = uuid4()
        recurring_meeting_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data={
                "id": str(transcript_id),
                "recurring_meeting_id": str(recurring_meeting_id),
                "meeting_date": "2024-01-15T10:00:00+00:00",
                "google_doc_id": "doc_123456",
                "raw_text": "テスト",
                "structured_data": {"entries": [{"speaker": "田中", "timestamp": "10:00", "text": "テスト"}]},
                "match_confidence": 0.85,
                "created_at": "2024-01-15T12:00:00+00:00",
            }
        )

        # Act
        result = await repository.get_by_id(transcript_id)

        # Assert
        assert result is not None
        assert result.id == transcript_id
        assert result.google_doc_id == "doc_123456"
        assert result.match_confidence == 0.85
        assert result.structured_data is not None
        assert len(result.structured_data.entries) == 1
        assert result.structured_data.entries[0].speaker == "田中"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しないIDの場合Noneを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=None)

        # Act
        result = await repository.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_recurring_meeting_success(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """定例MTGのトランスクリプト一覧を取得できる"""
        # Arrange
        recurring_meeting_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "recurring_meeting_id": str(recurring_meeting_id),
                    "meeting_date": "2024-01-22T10:00:00+00:00",
                    "google_doc_id": "doc_2",
                    "raw_text": "テスト2",
                    "structured_data": None,
                    "match_confidence": 0.9,
                    "created_at": "2024-01-22T12:00:00+00:00",
                },
                {
                    "id": str(uuid4()),
                    "recurring_meeting_id": str(recurring_meeting_id),
                    "meeting_date": "2024-01-15T10:00:00+00:00",
                    "google_doc_id": "doc_1",
                    "raw_text": "テスト1",
                    "structured_data": None,
                    "match_confidence": 0.85,
                    "created_at": "2024-01-15T12:00:00+00:00",
                },
            ]
        )

        # Act
        result = await repository.get_by_recurring_meeting(recurring_meeting_id)

        # Assert
        assert len(result) == 2
        assert result[0].google_doc_id == "doc_2"
        assert result[1].google_doc_id == "doc_1"

    @pytest.mark.asyncio
    async def test_get_by_recurring_meeting_with_limit(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """件数制限付きでトランスクリプト一覧を取得できる"""
        # Arrange
        recurring_meeting_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "recurring_meeting_id": str(recurring_meeting_id),
                    "meeting_date": "2024-01-22T10:00:00+00:00",
                    "google_doc_id": "doc_latest",
                    "raw_text": "最新",
                    "structured_data": None,
                    "match_confidence": 0.9,
                    "created_at": "2024-01-22T12:00:00+00:00",
                },
            ]
        )

        # Act
        result = await repository.get_by_recurring_meeting(recurring_meeting_id, limit=1)

        # Assert
        assert len(result) == 1
        mock_table.limit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_recurring_meeting_empty(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """トランスクリプトがない場合は空リストを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = await repository.get_by_recurring_meeting(uuid4())

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_date_range_success(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """指定期間内のトランスクリプトを取得できる"""
        # Arrange
        recurring_meeting_id = uuid4()
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "recurring_meeting_id": str(recurring_meeting_id),
                    "meeting_date": "2024-01-08T10:00:00+00:00",
                    "google_doc_id": "doc_1",
                    "raw_text": "1週目",
                    "structured_data": None,
                    "match_confidence": 0.8,
                    "created_at": "2024-01-08T12:00:00+00:00",
                },
                {
                    "id": str(uuid4()),
                    "recurring_meeting_id": str(recurring_meeting_id),
                    "meeting_date": "2024-01-15T10:00:00+00:00",
                    "google_doc_id": "doc_2",
                    "raw_text": "2週目",
                    "structured_data": None,
                    "match_confidence": 0.85,
                    "created_at": "2024-01-15T12:00:00+00:00",
                },
            ]
        )

        # Act
        result = await repository.get_by_date_range(recurring_meeting_id, start_date, end_date)

        # Assert
        assert len(result) == 2
        assert result[0].google_doc_id == "doc_1"
        assert result[1].google_doc_id == "doc_2"

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """トランスクリプトを正しく削除できる"""
        # Arrange
        transcript_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": str(transcript_id)}])

        # Act
        result = await repository.delete(transcript_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: MeetingTranscriptRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しないトランスクリプトを削除しようとするとFalseを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = await repository.delete(uuid4())

        # Assert
        assert result is False


class TestToEntity:
    """_to_entityメソッドのテスト"""

    @pytest.fixture
    def repository(self) -> MeetingTranscriptRepositoryImpl:
        """リポジトリインスタンスを返す"""
        return MeetingTranscriptRepositoryImpl(client=MagicMock())

    def test_to_entity_with_all_fields(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """全フィールドが正しく変換される"""
        # Arrange
        transcript_id = uuid4()
        recurring_meeting_id = uuid4()
        data = {
            "id": str(transcript_id),
            "recurring_meeting_id": str(recurring_meeting_id),
            "meeting_date": "2024-01-15T10:00:00+00:00",
            "google_doc_id": "doc_123",
            "raw_text": "テキスト",
            "structured_data": {
                "entries": [
                    {"speaker": "田中", "timestamp": "10:00", "text": "発言1"},
                    {"speaker": "鈴木", "timestamp": "10:05", "text": "発言2"},
                ]
            },
            "match_confidence": 0.95,
            "created_at": "2024-01-15T12:00:00+00:00",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.id == transcript_id
        assert result.recurring_meeting_id == recurring_meeting_id
        assert result.google_doc_id == "doc_123"
        assert result.match_confidence == 0.95
        assert result.structured_data is not None
        assert len(result.structured_data.entries) == 2
        assert result.structured_data.entries[0].speaker == "田中"
        assert result.structured_data.entries[1].speaker == "鈴木"

    def test_to_entity_with_none_structured_data(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """structured_dataがNoneの場合はNoneになる"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "recurring_meeting_id": str(uuid4()),
            "meeting_date": "2024-01-15T10:00:00+00:00",
            "google_doc_id": "doc_123",
            "raw_text": "テキスト",
            "structured_data": None,
            "match_confidence": 0.5,
            "created_at": "2024-01-15T12:00:00+00:00",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.structured_data is None

    def test_to_entity_with_z_timezone(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """Zタイムゾーン形式が正しく処理される"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "recurring_meeting_id": str(uuid4()),
            "meeting_date": "2024-01-15T10:00:00Z",
            "google_doc_id": "doc_123",
            "raw_text": "テキスト",
            "structured_data": None,
            "match_confidence": 0.5,
            "created_at": "2024-01-15T12:00:00Z",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.meeting_date.tzinfo is not None
        assert result.created_at.tzinfo is not None

    def test_to_entity_with_empty_entries(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """entriesが空配列の場合は空リストのTranscriptStructuredDataになる"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "recurring_meeting_id": str(uuid4()),
            "meeting_date": "2024-01-15T10:00:00+00:00",
            "google_doc_id": "doc_123",
            "raw_text": "テキスト",
            "structured_data": {"entries": []},
            "match_confidence": 0.5,
            "created_at": "2024-01-15T12:00:00+00:00",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.structured_data is not None
        assert result.structured_data.entries == []


class TestSerializeStructuredData:
    """_serialize_structured_dataメソッドのテスト"""

    @pytest.fixture
    def repository(self) -> MeetingTranscriptRepositoryImpl:
        """リポジトリインスタンスを返す"""
        return MeetingTranscriptRepositoryImpl(client=MagicMock())

    def test_serialize_with_data(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """TranscriptStructuredDataが正しくシリアライズされる"""
        # Arrange
        structured_data = TranscriptStructuredData(
            entries=[
                TranscriptEntry(speaker="田中", timestamp="10:00", text="発言1"),
            ]
        )

        # Act
        result = repository._serialize_structured_data(structured_data)

        # Assert
        assert result is not None
        assert "entries" in result
        assert len(result["entries"]) == 1
        assert result["entries"][0]["speaker"] == "田中"

    def test_serialize_with_none(self, repository: MeetingTranscriptRepositoryImpl) -> None:
        """Noneの場合はNoneを返す"""
        # Act
        result = repository._serialize_structured_data(None)

        # Assert
        assert result is None
