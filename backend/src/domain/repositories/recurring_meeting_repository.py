"""RecurringMeeting repository interface for domain layer.

Abstract base class defining the contract for recurring meeting persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.recurring_meeting import RecurringMeeting


class RecurringMeetingRepository(ABC):
    """定例MTGリポジトリのインターフェース.

    DDDのRepositoryパターンに従い、定例MTGの永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    def get_by_id(self, meeting_id: UUID, user_id: UUID) -> RecurringMeeting | None:
        """IDで定例MTGを取得する.

        Args:
            meeting_id: 定例MTGの一意識別子
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            見つかった場合はRecurringMeetingエンティティ、見つからない場合はNone
        """

    @abstractmethod
    def get_by_google_event_id(self, google_event_id: str, user_id: UUID) -> RecurringMeeting | None:
        """Google CalendarイベントIDで定例MTGを取得する.

        Args:
            google_event_id: Google CalendarのイベントID
            user_id: 所有ユーザーのID

        Returns:
            見つかった場合はRecurringMeetingエンティティ、見つからない場合はNone
        """

    @abstractmethod
    def get_all(self, user_id: UUID) -> list[RecurringMeeting]:
        """ユーザーの全定例MTGを取得する.

        Args:
            user_id: 所有ユーザーのID

        Returns:
            RecurringMeetingエンティティのリスト（次回開催日時の昇順）
        """

    @abstractmethod
    def create(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを作成する.

        Args:
            meeting: 作成するRecurringMeetingエンティティ

        Returns:
            作成されたRecurringMeetingエンティティ
        """

    @abstractmethod
    def update(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを更新する.

        Args:
            meeting: 更新するRecurringMeetingエンティティ

        Returns:
            更新されたRecurringMeetingエンティティ

        Raises:
            ValueError: 定例MTGが存在しない場合
        """

    @abstractmethod
    def delete(self, meeting_id: UUID, user_id: UUID) -> bool:
        """定例MTGを削除する.

        Args:
            meeting_id: 削除する定例MTGのID
            user_id: 所有ユーザーのID（RLSによるアクセス制御）

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """

    @abstractmethod
    def exists(self, meeting_id: UUID, user_id: UUID) -> bool:
        """定例MTGの存在を確認する.

        Args:
            meeting_id: 確認する定例MTGのID
            user_id: 所有ユーザーのID

        Returns:
            存在する場合はTrue、しない場合はFalse
        """

    @abstractmethod
    def get_unlinked(self, user_id: UUID) -> list[RecurringMeeting]:
        """エージェント未紐付けの定例MTGを取得する.

        Args:
            user_id: 所有ユーザーのID

        Returns:
            エージェントが紐付けられていない定例MTGのリスト
        """
