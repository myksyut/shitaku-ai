"""Knowledge entity for domain layer.

Pure Python entity without SQLAlchemy/Pydantic dependencies.
Following ADR-0001 clean architecture principles.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Knowledge:
    """ナレッジを表すエンティティ.

    Attributes:
        id: ナレッジの一意識別子
        agent_id: 紐付けられたエージェントのID
        user_id: 所有ユーザーのID
        original_text: 正規化前のテキスト
        normalized_text: 正規化後のテキスト
        meeting_date: MTG開催日時
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: UUID
    agent_id: UUID
    user_id: UUID
    original_text: str
    normalized_text: str
    meeting_date: datetime
    created_at: datetime
    updated_at: datetime | None = None

    def update_normalized_text(self, normalized_text: str) -> None:
        """正規化後テキストを更新する.

        Args:
            normalized_text: 新しい正規化後テキスト
        """
        self.normalized_text = normalized_text
        self.updated_at = datetime.now()

    def is_normalized(self) -> bool:
        """正規化が実行されたかどうかを判定する.

        Returns:
            正規化によってテキストが変更された場合はTrue
        """
        return self.original_text != self.normalized_text
