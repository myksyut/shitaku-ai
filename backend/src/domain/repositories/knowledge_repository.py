"""KnowledgeRepository interface for domain layer.

Abstract base class defining the contract for knowledge persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.knowledge import Knowledge


class KnowledgeRepository(ABC):
    """ナレッジリポジトリのインターフェース.

    DDDのRepositoryパターンに従い、ナレッジの永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    async def create(self, knowledge: Knowledge) -> Knowledge:
        """ナレッジを作成する.

        Args:
            knowledge: 作成するKnowledgeエンティティ

        Returns:
            作成されたKnowledgeエンティティ
        """

    @abstractmethod
    async def get_by_id(self, knowledge_id: UUID, user_id: UUID) -> Knowledge | None:
        """IDでナレッジを取得する.

        Args:
            knowledge_id: ナレッジの一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            見つかった場合はKnowledgeエンティティ、見つからない場合はNone
        """

    @abstractmethod
    async def get_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Knowledge]:
        """エージェントのナレッジ一覧を取得する.

        Args:
            agent_id: エージェントのID
            user_id: 所有ユーザーのID
            limit: 取得件数の上限（Noneの場合は制限なし）

        Returns:
            Knowledgeエンティティのリスト（日付降順）
        """

    @abstractmethod
    async def get_latest_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> Knowledge | None:
        """エージェントの最新ナレッジを取得する.

        Args:
            agent_id: エージェントのID
            user_id: 所有ユーザーのID

        Returns:
            最新のKnowledgeエンティティ、存在しない場合はNone
        """

    @abstractmethod
    async def delete(self, knowledge_id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除する.

        Args:
            knowledge_id: 削除するナレッジのID
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """
