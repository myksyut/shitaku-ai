"""Use cases for MeetingTranscript management.

Application layer use cases following clean architecture principles.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptStructuredData,
)
from src.domain.entities.recurring_meeting import RecurringMeeting
from src.domain.repositories.meeting_transcript_repository import (
    MeetingTranscriptRepository,
)
from src.domain.repositories.recurring_meeting_repository import (
    RecurringMeetingRepository,
)
from src.domain.services.matching_algorithm import calculate_match_confidence
from src.domain.services.transcript_parser import (
    extract_speakers,
    parse_to_structured_data,
)
from src.infrastructure.external.google_docs_client import GoogleDocsClient
from src.infrastructure.external.google_drive_client import DriveFile, GoogleDriveClient


class CreateTranscriptUseCase:
    """トランスクリプト作成ユースケース."""

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(self, transcript: MeetingTranscript) -> MeetingTranscript:
        """トランスクリプトを作成する."""
        return await self.repository.create(transcript)


class GetTranscriptUseCase:
    """トランスクリプト取得ユースケース."""

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(self, transcript_id: UUID) -> MeetingTranscript | None:
        """IDでトランスクリプトを取得する."""
        return await self.repository.get_by_id(transcript_id)


class GetTranscriptsByRecurringMeetingUseCase:
    """定例MTGのトランスクリプト一覧取得ユースケース."""

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        recurring_meeting_id: UUID,
        limit: int | None = None,
    ) -> list[MeetingTranscript]:
        """定例MTGのトランスクリプト一覧を取得する."""
        return await self.repository.get_by_recurring_meeting(recurring_meeting_id, limit)


class GetTranscriptsByDateRangeUseCase:
    """日付範囲でのトランスクリプト一覧取得ユースケース."""

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        recurring_meeting_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[MeetingTranscript]:
        """指定期間内のトランスクリプト一覧を取得する."""
        return await self.repository.get_by_date_range(recurring_meeting_id, start_date, end_date)


class DeleteTranscriptUseCase:
    """トランスクリプト削除ユースケース."""

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(self, transcript_id: UUID) -> bool:
        """トランスクリプトを削除する."""
        return await self.repository.delete(transcript_id)


class GetTranscriptsNeedingConfirmationUseCase:
    """手動確認が必要なトランスクリプト一覧取得ユースケース.

    match_confidenceが0.7未満のトランスクリプトを抽出する。
    """

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        recurring_meeting_id: UUID,
    ) -> list[MeetingTranscript]:
        """手動確認が必要なトランスクリプト一覧を取得する."""
        all_transcripts = await self.repository.get_by_recurring_meeting(recurring_meeting_id, None)
        return [t for t in all_transcripts if t.needs_manual_confirmation()]


@dataclass
class SyncResult:
    """同期結果."""

    synced_count: int
    skipped_count: int
    error_count: int
    synced_transcripts: list[MeetingTranscript]


class SyncTranscriptsUseCase:
    """トランスクリプト同期ユースケース.

    Google DriveからMeet Recordingsフォルダを検索し、
    Google Docsのテキストを取得して構造化、
    定例MTGとのマッチングを行いDBに保存する。
    """

    AUTO_LINK_THRESHOLD = 0.7

    def __init__(
        self,
        transcript_repository: MeetingTranscriptRepository,
        recurring_meeting_repository: RecurringMeetingRepository,
        drive_client: GoogleDriveClient,
        docs_client: GoogleDocsClient,
    ) -> None:
        self.transcript_repository = transcript_repository
        self.recurring_meeting_repository = recurring_meeting_repository
        self.drive_client = drive_client
        self.docs_client = docs_client

    async def execute(self, user_id: UUID) -> SyncResult:
        """トランスクリプトを同期する.

        1. Google DriveからMeet Recordingsフォルダのファイル一覧を取得
        2. 各ファイルのテキストを取得してパース
        3. 定例MTG一覧を取得してマッチング
        4. 信頼度0.7以上は自動紐付け、未満はneeds_confirmation=True
        5. 重複はgoogle_doc_idでスキップ

        Args:
            user_id: ユーザーID

        Returns:
            SyncResult: 同期結果
        """
        synced_count = 0
        skipped_count = 0
        error_count = 0
        synced_transcripts: list[MeetingTranscript] = []

        # 1. Google DriveからMeet Recordingsファイル一覧を取得
        drive_files = await self.drive_client.search_transcript_files()

        # 2. 定例MTG一覧を取得
        recurring_meetings = await self.recurring_meeting_repository.get_all(user_id)

        # 3. 各ファイルを処理
        for drive_file in drive_files:
            # 重複チェック
            existing = await self.transcript_repository.get_by_google_doc_id(drive_file.id, user_id)
            if existing:
                skipped_count += 1
                continue

            # Google Docsのテキストを取得
            raw_text = await self.docs_client.get_document_text(drive_file.id)
            if raw_text is None:
                error_count += 1
                continue

            # パースして構造化
            structured_data = parse_to_structured_data(raw_text)
            speakers = extract_speakers(raw_text)

            # 最適な定例MTGを見つける
            best_match = self._find_best_match(drive_file, speakers, recurring_meetings)

            if best_match is None:
                # マッチする定例MTGがない場合はスキップ
                error_count += 1
                continue

            recurring_meeting, confidence = best_match

            # トランスクリプトを作成
            transcript = self._create_transcript(
                drive_file=drive_file,
                raw_text=raw_text,
                structured_data=structured_data,
                recurring_meeting_id=recurring_meeting.id,
                confidence=confidence,
            )

            # DBに保存
            created = await self.transcript_repository.create(transcript)
            synced_transcripts.append(created)
            synced_count += 1

        return SyncResult(
            synced_count=synced_count,
            skipped_count=skipped_count,
            error_count=error_count,
            synced_transcripts=synced_transcripts,
        )

    def _find_best_match(
        self,
        drive_file: DriveFile,
        speakers: list[str],
        recurring_meetings: list[RecurringMeeting],
    ) -> tuple[RecurringMeeting, float] | None:
        """最適な定例MTGを見つける.

        各定例MTGとの信頼度を計算し、最も高いものを返す。

        Args:
            drive_file: Google Driveファイル情報
            speakers: トランスクリプトの話者リスト
            recurring_meetings: 定例MTG一覧

        Returns:
            (定例MTG, 信頼度)のタプル。マッチするものがない場合はNone。
        """
        if not recurring_meetings:
            return None

        best_match: tuple[RecurringMeeting, float] | None = None
        best_confidence = 0.0

        for meeting in recurring_meetings:
            # 参加者のメールアドレスリストを取得
            attendee_emails = [a.email for a in meeting.attendees]

            # 信頼度を計算
            confidence = calculate_match_confidence(
                doc_name=drive_file.name,
                doc_created=drive_file.created_time,
                event_summary=meeting.title,
                event_datetime=meeting.next_occurrence,
                event_attendees=attendee_emails,
                transcript_speakers=speakers,
            )

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = (meeting, confidence)

        return best_match

    def _create_transcript(
        self,
        drive_file: DriveFile,
        raw_text: str,
        structured_data: TranscriptStructuredData | None,
        recurring_meeting_id: UUID,
        confidence: float,
    ) -> MeetingTranscript:
        """トランスクリプトエンティティを作成する."""
        return MeetingTranscript(
            id=uuid4(),
            recurring_meeting_id=recurring_meeting_id,
            meeting_date=drive_file.created_time,
            google_doc_id=drive_file.id,
            raw_text=raw_text,
            structured_data=structured_data,
            match_confidence=confidence,
            created_at=datetime.now(UTC),
        )


class LinkTranscriptUseCase:
    """トランスクリプト手動紐付けユースケース.

    手動で定例MTGへの紐付けを行い、信頼度を1.0に設定する。
    """

    def __init__(
        self,
        transcript_repository: MeetingTranscriptRepository,
        recurring_meeting_repository: RecurringMeetingRepository,
    ) -> None:
        self.transcript_repository = transcript_repository
        self.recurring_meeting_repository = recurring_meeting_repository

    async def execute(
        self,
        transcript_id: UUID,
        recurring_meeting_id: UUID,
        user_id: UUID,
    ) -> MeetingTranscript:
        """トランスクリプトを定例MTGに紐付ける.

        Args:
            transcript_id: トランスクリプトID
            recurring_meeting_id: 紐付け先の定例MTG ID
            user_id: ユーザーID（認可チェック用）

        Returns:
            更新されたMeetingTranscriptエンティティ

        Raises:
            ValueError: トランスクリプトまたは定例MTGが見つからない場合
        """
        # トランスクリプトを取得
        transcript = await self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise ValueError("Transcript not found")

        # 定例MTGを取得（user_idでアクセス権を確認）
        recurring_meeting = await self.recurring_meeting_repository.get_by_id(recurring_meeting_id, user_id)
        if recurring_meeting is None:
            raise ValueError("Recurring meeting not found or access denied")

        # 紐付けを更新（手動紐付けは信頼度1.0）
        transcript.recurring_meeting_id = recurring_meeting_id
        transcript.match_confidence = 1.0

        return await self.transcript_repository.update(transcript)


class GetPendingTranscriptsUseCase:
    """手動確認待ちトランスクリプト一覧取得ユースケース.

    match_confidenceが0.7未満のトランスクリプトを全て取得する。
    """

    def __init__(self, repository: MeetingTranscriptRepository) -> None:
        self.repository = repository

    async def execute(self, user_id: UUID) -> list[MeetingTranscript]:
        """手動確認待ちトランスクリプト一覧を取得する."""
        return await self.repository.get_needing_confirmation(user_id)
