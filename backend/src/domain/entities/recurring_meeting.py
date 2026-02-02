"""RecurringMeeting entity for domain layer.

Pure Python entity without SQLAlchemy/Pydantic dependencies.
Following ADR-0001 clean architecture principles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

MeetingFrequency = Literal["weekly", "biweekly", "monthly"]


@dataclass
class RecurringMeeting:
    """定例MTGを表すエンティティ.

    Attributes:
        id: 定例MTGの一意識別子
        user_id: 所有ユーザーのID
        google_event_id: Google CalendarのイベントID
        title: MTGタイトル
        rrule: RFC 5545形式の繰り返しルール
        frequency: 開催頻度（weekly/biweekly/monthly）
        attendees: 参加者のメールアドレスリスト
        next_occurrence: 次回開催日時
        agent_id: 紐付けられたエージェントID
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: UUID
    user_id: UUID
    google_event_id: str
    title: str
    rrule: str
    frequency: MeetingFrequency
    next_occurrence: datetime
    created_at: datetime
    attendees: list[str] = field(default_factory=list)
    agent_id: UUID | None = None
    updated_at: datetime | None = None

    def link_agent(self, agent_id: UUID) -> None:
        """エージェントを紐付ける.

        Args:
            agent_id: 紐付けるエージェントのID
        """
        self.agent_id = agent_id
        self.updated_at = datetime.now()

    def unlink_agent(self) -> None:
        """エージェントの紐付けを解除する."""
        self.agent_id = None
        self.updated_at = datetime.now()

    def update_next_occurrence(self, next_occurrence: datetime) -> None:
        """次回開催日時を更新する.

        Args:
            next_occurrence: 新しい次回開催日時
        """
        self.next_occurrence = next_occurrence
        self.updated_at = datetime.now()

    def update_attendees(self, attendees: list[str]) -> None:
        """参加者リストを更新する.

        Args:
            attendees: 新しい参加者リスト
        """
        self.attendees = attendees
        self.updated_at = datetime.now()
