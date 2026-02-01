"""MeetingNoteRepository interface for domain layer.

Abstract base class defining the contract for meeting note persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.meeting_note import MeetingNote


class MeetingNoteRepository(ABC):
    """議事録リポジトリのインターフェース.

    DDDのRepositoryパターンに従い、議事録の永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    async def create(self, note: MeetingNote) -> MeetingNote:
        """議事録を作成する.

        Args:
            note: 作成するMeetingNoteエンティティ

        Returns:
            作成されたMeetingNoteエンティティ
        """

    @abstractmethod
    async def get_by_id(self, note_id: UUID, user_id: UUID) -> MeetingNote | None:
        """IDで議事録を取得する.

        Args:
            note_id: 議事録の一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            見つかった場合はMeetingNoteエンティティ、見つからない場合はNone
        """

    @abstractmethod
    async def get_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[MeetingNote]:
        """エージェントの議事録一覧を取得する.

        Args:
            agent_id: エージェントのID
            user_id: 所有ユーザーのID
            limit: 取得件数の上限（Noneの場合は制限なし）

        Returns:
            MeetingNoteエンティティのリスト（日付降順）
        """

    @abstractmethod
    async def get_latest_by_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> MeetingNote | None:
        """エージェントの最新議事録を取得する.

        Args:
            agent_id: エージェントのID
            user_id: 所有ユーザーのID

        Returns:
            最新のMeetingNoteエンティティ、存在しない場合はNone
        """

    @abstractmethod
    async def delete(self, note_id: UUID, user_id: UUID) -> bool:
        """議事録を削除する.

        Args:
            note_id: 削除する議事録のID
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """
