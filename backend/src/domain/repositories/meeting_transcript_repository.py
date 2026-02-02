"""MeetingTranscriptRepository interface for domain layer.

Abstract base class defining the contract for meeting transcript persistence operations.
Implementations should be provided in the infrastructure layer.
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.meeting_transcript import MeetingTranscript


class MeetingTranscriptRepository(ABC):
    """会議トランスクリプトリポジトリのインターフェース.

    DDDのRepositoryパターンに従い、トランスクリプトの永続化操作を定義。
    具体的な実装はインフラ層で提供される。
    """

    @abstractmethod
    async def create(self, transcript: MeetingTranscript) -> MeetingTranscript:
        """トランスクリプトを作成する.

        Args:
            transcript: 作成するMeetingTranscriptエンティティ

        Returns:
            作成されたMeetingTranscriptエンティティ
        """

    @abstractmethod
    async def get_by_id(self, transcript_id: UUID) -> MeetingTranscript | None:
        """IDでトランスクリプトを取得する.

        Args:
            transcript_id: トランスクリプトの一意識別子

        Returns:
            見つかった場合はMeetingTranscriptエンティティ、見つからない場合はNone
        """

    @abstractmethod
    async def get_by_recurring_meeting(
        self,
        recurring_meeting_id: UUID,
        limit: int | None = None,
    ) -> list[MeetingTranscript]:
        """定例MTGのトランスクリプト一覧を取得する.

        Args:
            recurring_meeting_id: 定例MTGのID
            limit: 取得件数の上限（Noneの場合は制限なし）

        Returns:
            MeetingTranscriptエンティティのリスト（日付降順）
        """

    @abstractmethod
    async def get_by_date_range(
        self,
        recurring_meeting_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[MeetingTranscript]:
        """指定期間内のトランスクリプトを取得する.

        Args:
            recurring_meeting_id: 定例MTGのID
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            MeetingTranscriptエンティティのリスト（日付昇順）
        """

    @abstractmethod
    async def get_by_google_doc_id(
        self,
        google_doc_id: str,
        user_id: UUID,
    ) -> MeetingTranscript | None:
        """Google Doc IDでトランスクリプトを取得する.

        Args:
            google_doc_id: Google DocsのドキュメントID
            user_id: ユーザーID（RLSフィルタリング用）

        Returns:
            見つかった場合はMeetingTranscriptエンティティ、見つからない場合はNone
        """

    @abstractmethod
    async def update(self, transcript: MeetingTranscript) -> MeetingTranscript:
        """トランスクリプトを更新する.

        Args:
            transcript: 更新するMeetingTranscriptエンティティ

        Returns:
            更新されたMeetingTranscriptエンティティ
        """

    @abstractmethod
    async def get_needing_confirmation(
        self,
        user_id: UUID,
    ) -> list[MeetingTranscript]:
        """手動確認が必要なトランスクリプト一覧を取得する.

        match_confidenceが0.7未満のトランスクリプトを取得。

        Args:
            user_id: ユーザーID（RLSフィルタリング用）

        Returns:
            手動確認が必要なMeetingTranscriptエンティティのリスト
        """

    @abstractmethod
    async def delete(self, transcript_id: UUID) -> bool:
        """トランスクリプトを削除する.

        Args:
            transcript_id: 削除するトランスクリプトのID

        Returns:
            削除成功時はTrue、見つからない場合はFalse
        """
