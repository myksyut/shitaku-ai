"""Agenda entity for domain layer.

Pure Python entity without SQLAlchemy/Pydantic dependencies.
Following ADR-0001 clean architecture principles.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Agenda:
    """アジェンダを表すエンティティ.

    Attributes:
        id: アジェンダの一意識別子
        agent_id: 紐付けられたエージェントのID
        user_id: 所有ユーザーのID
        content: アジェンダの内容（マークダウン形式）
        source_note_id: 生成元の議事録ID（存在しない場合はNone）
        generated_at: アジェンダが生成された日時
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: UUID
    agent_id: UUID
    user_id: UUID
    content: str
    generated_at: datetime
    created_at: datetime
    source_note_id: UUID | None = None
    updated_at: datetime | None = None

    def update_content(self, content: str) -> None:
        """アジェンダ内容を更新する.

        Args:
            content: 新しいアジェンダ内容
        """
        self.content = content
        self.updated_at = datetime.now()
