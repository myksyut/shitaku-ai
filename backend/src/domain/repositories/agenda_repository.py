"""Agenda repository interface for domain layer.

Abstract base class defining the contract for agenda persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.agenda import Agenda


class AgendaRepository(ABC):
    """アジェンダリポジトリのインターフェース.

    DDDのRepositoryパターンに従い、アジェンダの永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    async def create(self, agenda: Agenda) -> Agenda:
        """アジェンダを作成する.

        Args:
            agenda: 作成するAgendaエンティティ

        Returns:
            作成されたAgendaエンティティ
        """

    @abstractmethod
    async def get_by_id(self, agenda_id: UUID, user_id: UUID) -> Agenda | None:
        """IDでアジェンダを取得する.

        Args:
            agenda_id: アジェンダの一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            見つかった場合はAgendaエンティティ、見つからない場合はNone
        """

    @abstractmethod
    async def get_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Agenda]:
        """エージェントのアジェンダ一覧を取得する.

        Args:
            agent_id: エージェントの一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）
            limit: 取得件数の上限（Noneの場合は全件）

        Returns:
            Agendaエンティティのリスト（生成日時の降順）
        """

    @abstractmethod
    async def update(self, agenda: Agenda) -> Agenda:
        """アジェンダを更新する.

        Args:
            agenda: 更新するAgendaエンティティ

        Returns:
            更新されたAgendaエンティティ

        Raises:
            ValueError: アジェンダが存在しない場合
        """

    @abstractmethod
    async def delete(self, agenda_id: UUID, user_id: UUID) -> bool:
        """アジェンダを削除する.

        Args:
            agenda_id: 削除するアジェンダのID
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """
