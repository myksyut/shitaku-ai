"""Agent repository interface for domain layer.

Abstract base class defining the contract for agent persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.agent import Agent


class AgentRepository(ABC):
    """エージェントリポジトリのインターフェース.

    DDDのRepositoryパターンに従い、エージェントの永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    def get_by_id(self, agent_id: UUID, user_id: UUID) -> Agent | None:
        """IDでエージェントを取得する.

        Args:
            agent_id: エージェントの一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            見つかった場合はAgentエンティティ、見つからない場合はNone
        """

    @abstractmethod
    def get_all(self, user_id: UUID) -> list[Agent]:
        """ユーザーの全エージェントを取得する.

        Args:
            user_id: 所有ユーザーのID

        Returns:
            Agentエンティティのリスト（作成日時の降順）
        """

    @abstractmethod
    def create(self, agent: Agent) -> Agent:
        """エージェントを作成する.

        Args:
            agent: 作成するAgentエンティティ

        Returns:
            作成されたAgentエンティティ
        """

    @abstractmethod
    def update(self, agent: Agent) -> Agent:
        """エージェントを更新する.

        Args:
            agent: 更新するAgentエンティティ

        Returns:
            更新されたAgentエンティティ

        Raises:
            ValueError: エージェントが存在しない場合
        """

    @abstractmethod
    def delete(self, agent_id: UUID, user_id: UUID) -> bool:
        """エージェントを削除する.

        関連する議事録・アジェンダもカスケード削除される。

        Args:
            agent_id: 削除するエージェントのID
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """

    @abstractmethod
    def exists(self, agent_id: UUID, user_id: UUID) -> bool:
        """エージェントの存在を確認する.

        Args:
            agent_id: 確認するエージェントのID
            user_id: 所有ユーザーのID

        Returns:
            存在する場合はTrue、しない場合はFalse
        """
