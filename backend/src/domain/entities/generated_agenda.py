"""生成アジェンダエンティティ."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class AgendaStatus(str, Enum):
    """アジェンダステータス."""

    DRAFT = "draft"
    SENT = "sent"
    REVIEWED = "reviewed"


@dataclass
class AgendaSource:
    """アジェンダのソース情報.

    Attributes:
        source_type: ソースタイプ（transcript, slack, manual）
        source_id: ソースID
        summary: 要約
    """

    source_type: str
    source_id: str
    summary: str


@dataclass
class GeneratedAgenda:
    """生成アジェンダエンティティ.

    Attributes:
        id: アジェンダID
        recurring_meeting_id: 紐付けられた定例MTG ID
        target_date: 対象日時
        agenda_content: アジェンダ内容（JSON）
        sources: ソース情報リスト
        status: ステータス
        delivered_via: 配信方法
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: UUID
    recurring_meeting_id: UUID
    target_date: datetime
    agenda_content: dict[str, Any]
    sources: list[AgendaSource]
    status: AgendaStatus
    delivered_via: str | None
    created_at: datetime
    updated_at: datetime | None

    def mark_as_sent(self, via: str) -> None:
        """送信済みにマークする.

        Args:
            via: 配信方法（slack, email等）
        """
        self.status = AgendaStatus.SENT
        self.delivered_via = via
        self.updated_at = datetime.now()

    def mark_as_reviewed(self) -> None:
        """レビュー済みにマークする."""
        self.status = AgendaStatus.REVIEWED
        self.updated_at = datetime.now()
