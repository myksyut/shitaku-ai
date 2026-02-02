"""Unit tests for TranscriptUseCases.

Tests for application layer use cases following clean architecture principles.
Repository dependencies are mocked to ensure unit test isolation.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.transcript_use_cases import (
    CreateTranscriptUseCase,
    DeleteTranscriptUseCase,
    GetTranscriptsByDateRangeUseCase,
    GetTranscriptsByRecurringMeetingUseCase,
    GetTranscriptsNeedingConfirmationUseCase,
    GetTranscriptUseCase,
)
from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptEntry,
    TranscriptStructuredData,
)
from src.domain.repositories.meeting_transcript_repository import (
    MeetingTranscriptRepository,
)


@pytest.fixture
def mock_repository() -> MagicMock:
    """モックリポジトリを作成する."""
    return MagicMock(spec=MeetingTranscriptRepository)


@pytest.fixture
def sample_transcript() -> MeetingTranscript:
    """サンプルトランスクリプトを作成する."""
    return MeetingTranscript(
        id=uuid4(),
        recurring_meeting_id=uuid4(),
        meeting_date=datetime(2024, 1, 15, 10, 0, 0),
        google_doc_id="doc_123",
        raw_text="テスト議事録",
        structured_data=TranscriptStructuredData(
            entries=[
                TranscriptEntry(speaker="田中", timestamp="10:00", text="こんにちは"),
            ]
        ),
        match_confidence=0.85,
        created_at=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def low_confidence_transcript() -> MeetingTranscript:
    """低信頼度トランスクリプトを作成する."""
    return MeetingTranscript(
        id=uuid4(),
        recurring_meeting_id=uuid4(),
        meeting_date=datetime(2024, 1, 16, 10, 0, 0),
        google_doc_id="doc_456",
        raw_text="低信頼度議事録",
        structured_data=None,
        match_confidence=0.5,
        created_at=datetime(2024, 1, 16, 12, 0, 0),
    )


class TestCreateTranscriptUseCase:
    """CreateTranscriptUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_create_transcript_successfully(
        self, mock_repository: MagicMock, sample_transcript: MeetingTranscript
    ) -> None:
        """トランスクリプトを正常に作成できること."""
        # Arrange
        mock_repository.create = AsyncMock(return_value=sample_transcript)
        use_case = CreateTranscriptUseCase(mock_repository)

        # Act
        result = await use_case.execute(sample_transcript)

        # Assert
        assert result == sample_transcript
        mock_repository.create.assert_called_once_with(sample_transcript)


class TestGetTranscriptUseCase:
    """GetTranscriptUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_get_transcript_found(self, mock_repository: MagicMock, sample_transcript: MeetingTranscript) -> None:
        """トランスクリプトが見つかった場合に返すこと."""
        # Arrange
        mock_repository.get_by_id = AsyncMock(return_value=sample_transcript)
        use_case = GetTranscriptUseCase(mock_repository)

        # Act
        result = await use_case.execute(sample_transcript.id)

        # Assert
        assert result == sample_transcript
        mock_repository.get_by_id.assert_called_once_with(sample_transcript.id)

    @pytest.mark.asyncio
    async def test_get_transcript_not_found(self, mock_repository: MagicMock) -> None:
        """トランスクリプトが見つからない場合にNoneを返すこと."""
        # Arrange
        mock_repository.get_by_id = AsyncMock(return_value=None)
        use_case = GetTranscriptUseCase(mock_repository)
        transcript_id = uuid4()

        # Act
        result = await use_case.execute(transcript_id)

        # Assert
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(transcript_id)


class TestGetTranscriptsByRecurringMeetingUseCase:
    """GetTranscriptsByRecurringMeetingUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_get_transcripts_by_recurring_meeting(
        self, mock_repository: MagicMock, sample_transcript: MeetingTranscript
    ) -> None:
        """定例MTGのトランスクリプト一覧を取得できること."""
        # Arrange
        transcripts = [sample_transcript]
        mock_repository.get_by_recurring_meeting = AsyncMock(return_value=transcripts)
        use_case = GetTranscriptsByRecurringMeetingUseCase(mock_repository)
        recurring_meeting_id = sample_transcript.recurring_meeting_id

        # Act
        result = await use_case.execute(recurring_meeting_id)

        # Assert
        assert result == transcripts
        mock_repository.get_by_recurring_meeting.assert_called_once_with(recurring_meeting_id, None)

    @pytest.mark.asyncio
    async def test_get_transcripts_with_limit(
        self, mock_repository: MagicMock, sample_transcript: MeetingTranscript
    ) -> None:
        """limit指定でトランスクリプト一覧を取得できること."""
        # Arrange
        transcripts = [sample_transcript]
        mock_repository.get_by_recurring_meeting = AsyncMock(return_value=transcripts)
        use_case = GetTranscriptsByRecurringMeetingUseCase(mock_repository)
        recurring_meeting_id = sample_transcript.recurring_meeting_id

        # Act
        result = await use_case.execute(recurring_meeting_id, limit=5)

        # Assert
        assert result == transcripts
        mock_repository.get_by_recurring_meeting.assert_called_once_with(recurring_meeting_id, 5)


class TestGetTranscriptsByDateRangeUseCase:
    """GetTranscriptsByDateRangeUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_get_transcripts_by_date_range(
        self, mock_repository: MagicMock, sample_transcript: MeetingTranscript
    ) -> None:
        """日付範囲でトランスクリプト一覧を取得できること."""
        # Arrange
        transcripts = [sample_transcript]
        mock_repository.get_by_date_range = AsyncMock(return_value=transcripts)
        use_case = GetTranscriptsByDateRangeUseCase(mock_repository)
        recurring_meeting_id = sample_transcript.recurring_meeting_id
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        end_date = datetime(2024, 1, 31, 23, 59, 59)

        # Act
        result = await use_case.execute(recurring_meeting_id, start_date, end_date)

        # Assert
        assert result == transcripts
        mock_repository.get_by_date_range.assert_called_once_with(recurring_meeting_id, start_date, end_date)


class TestDeleteTranscriptUseCase:
    """DeleteTranscriptUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_delete_transcript_successfully(self, mock_repository: MagicMock) -> None:
        """トランスクリプトを正常に削除できること."""
        # Arrange
        mock_repository.delete = AsyncMock(return_value=True)
        use_case = DeleteTranscriptUseCase(mock_repository)
        transcript_id = uuid4()

        # Act
        result = await use_case.execute(transcript_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(transcript_id)

    @pytest.mark.asyncio
    async def test_delete_transcript_not_found(self, mock_repository: MagicMock) -> None:
        """削除対象が見つからない場合にFalseを返すこと."""
        # Arrange
        mock_repository.delete = AsyncMock(return_value=False)
        use_case = DeleteTranscriptUseCase(mock_repository)
        transcript_id = uuid4()

        # Act
        result = await use_case.execute(transcript_id)

        # Assert
        assert result is False
        mock_repository.delete.assert_called_once_with(transcript_id)


class TestGetTranscriptsNeedingConfirmationUseCase:
    """GetTranscriptsNeedingConfirmationUseCaseのテスト."""

    @pytest.mark.asyncio
    async def test_get_transcripts_needing_confirmation(
        self,
        mock_repository: MagicMock,
        sample_transcript: MeetingTranscript,
        low_confidence_transcript: MeetingTranscript,
    ) -> None:
        """手動確認が必要なトランスクリプトのみを返すこと."""
        # Arrange
        # sample_transcript: match_confidence=0.85 (自動紐付け)
        # low_confidence_transcript: match_confidence=0.5 (手動確認必要)
        all_transcripts = [sample_transcript, low_confidence_transcript]
        mock_repository.get_by_recurring_meeting = AsyncMock(return_value=all_transcripts)
        use_case = GetTranscriptsNeedingConfirmationUseCase(mock_repository)
        recurring_meeting_id = sample_transcript.recurring_meeting_id

        # Act
        result = await use_case.execute(recurring_meeting_id)

        # Assert
        assert len(result) == 1
        assert result[0] == low_confidence_transcript
        assert result[0].needs_manual_confirmation() is True

    @pytest.mark.asyncio
    async def test_get_transcripts_needing_confirmation_empty(
        self,
        mock_repository: MagicMock,
        sample_transcript: MeetingTranscript,
    ) -> None:
        """手動確認が必要なトランスクリプトがない場合は空リストを返すこと."""
        # Arrange
        all_transcripts = [sample_transcript]  # match_confidence=0.85
        mock_repository.get_by_recurring_meeting = AsyncMock(return_value=all_transcripts)
        use_case = GetTranscriptsNeedingConfirmationUseCase(mock_repository)
        recurring_meeting_id = sample_transcript.recurring_meeting_id

        # Act
        result = await use_case.execute(recurring_meeting_id)

        # Assert
        assert len(result) == 0
