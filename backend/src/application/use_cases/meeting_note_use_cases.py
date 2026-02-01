"""Use cases for MeetingNote management.

Application layer use cases following clean architecture principles.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.meeting_note import MeetingNote
from src.domain.repositories.agent_repository import AgentRepository
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.meeting_note_repository import MeetingNoteRepository
from src.domain.services.normalization_service import NormalizationError, NormalizationService

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """アップロード結果."""

    note: MeetingNote
    normalization_warning: str | None
    replacement_count: int


class UploadMeetingNoteUseCase:
    """議事録アップロードユースケース（正規化処理含む）."""

    def __init__(
        self,
        note_repository: MeetingNoteRepository,
        dictionary_repository: DictionaryRepository,
        agent_repository: AgentRepository,
        normalization_service: NormalizationService,
    ) -> None:
        self.note_repository = note_repository
        self.dictionary_repository = dictionary_repository
        self.agent_repository = agent_repository
        self.normalization_service = normalization_service

    async def execute(
        self,
        user_id: UUID,
        agent_id: UUID,
        text: str,
        meeting_date: datetime,
    ) -> UploadResult:
        """議事録をアップロードする（正規化処理含む）."""
        # エージェントの存在確認
        agent = self.agent_repository.get_by_id(agent_id, user_id)
        if not agent:
            raise ValueError("Agent not found")

        # 辞書を取得
        dictionary = await self.dictionary_repository.get_all(user_id)

        # 正規化処理
        normalized_text = text
        normalization_warning: str | None = None
        replacement_count = 0

        try:
            result = self.normalization_service.normalize(text, dictionary)
            normalized_text = result.normalized_text
            replacement_count = result.replacement_count
        except NormalizationError as e:
            logger.warning(f"Normalization failed, using original text: {e}")
            normalization_warning = "正規化処理に失敗しました。元のテキストを保存しました。"

        # 議事録を作成
        note = MeetingNote(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            original_text=text,
            normalized_text=normalized_text,
            meeting_date=meeting_date,
            created_at=datetime.now(),
        )

        saved_note = await self.note_repository.create(note)

        return UploadResult(
            note=saved_note,
            normalization_warning=normalization_warning,
            replacement_count=replacement_count,
        )


class GetMeetingNotesUseCase:
    """議事録一覧取得ユースケース."""

    def __init__(self, repository: MeetingNoteRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[MeetingNote]:
        """エージェントの議事録一覧を取得する."""
        return await self.repository.get_by_agent(agent_id, user_id, limit)


class GetMeetingNoteUseCase:
    """議事録取得ユースケース."""

    def __init__(self, repository: MeetingNoteRepository) -> None:
        self.repository = repository

    async def execute(self, note_id: UUID, user_id: UUID) -> MeetingNote | None:
        """IDで議事録を取得する."""
        return await self.repository.get_by_id(note_id, user_id)


class DeleteMeetingNoteUseCase:
    """議事録削除ユースケース."""

    def __init__(self, repository: MeetingNoteRepository) -> None:
        self.repository = repository

    async def execute(self, note_id: UUID, user_id: UUID) -> bool:
        """議事録を削除する."""
        return await self.repository.delete(note_id, user_id)
