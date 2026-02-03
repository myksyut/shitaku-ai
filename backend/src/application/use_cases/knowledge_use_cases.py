"""Use cases for Knowledge management.

Application layer use cases following clean architecture principles.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.knowledge import Knowledge
from src.domain.repositories.agent_repository import AgentRepository
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.services.normalization_service import NormalizationError, NormalizationService

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """アップロード結果."""

    knowledge: Knowledge
    normalization_warning: str | None
    replacement_count: int


class UploadKnowledgeUseCase:
    """ナレッジアップロードユースケース（正規化処理含む）."""

    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        dictionary_repository: DictionaryRepository,
        agent_repository: AgentRepository,
        normalization_service: NormalizationService,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.dictionary_repository = dictionary_repository
        self.agent_repository = agent_repository
        self.normalization_service = normalization_service

    async def execute(
        self,
        user_id: UUID,
        agent_id: UUID,
        text: str,
    ) -> UploadResult:
        """ナレッジをアップロードする（正規化処理含む）."""
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

        # ナレッジを作成（meeting_dateは作成日時を使用）
        now = datetime.now()
        knowledge = Knowledge(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            original_text=text,
            normalized_text=normalized_text,
            meeting_date=now,
            created_at=now,
        )

        saved_knowledge = await self.knowledge_repository.create(knowledge)

        return UploadResult(
            knowledge=saved_knowledge,
            normalization_warning=normalization_warning,
            replacement_count=replacement_count,
        )


class GetKnowledgeListUseCase:
    """ナレッジ一覧取得ユースケース."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Knowledge]:
        """エージェントのナレッジ一覧を取得する."""
        return await self.repository.get_by_agent(agent_id, user_id, limit)


class GetKnowledgeUseCase:
    """ナレッジ取得ユースケース."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    async def execute(self, knowledge_id: UUID, user_id: UUID) -> Knowledge | None:
        """IDでナレッジを取得する."""
        return await self.repository.get_by_id(knowledge_id, user_id)


class DeleteKnowledgeUseCase:
    """ナレッジ削除ユースケース."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    async def execute(self, knowledge_id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除する."""
        return await self.repository.delete(knowledge_id, user_id)
