"""RecurringMeeting entity for domain layer.

Pure Python entity without external dependencies.
Following ADR-0001 clean architecture principles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class MeetingFrequency(Enum):
    """定例MTGの頻度."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


@dataclass
class Attendee:
    """参加者情報.

    Attributes:
        email: 参加者のメールアドレス.
        name: 参加者の表示名（オプション）.
    """

    email: str
    name: str | None = None


@dataclass
class RecurringMeeting:
    """定例MTGを表すエンティティ.

    Attributes:
        id: 定例MTGの一意識別子.
        user_id: 所有ユーザーのID.
        google_event_id: Google CalendarのイベントID.
        title: MTGタイトル.
        rrule: iCalendar形式の繰り返しルール.
        frequency: MTGの頻度（weekly, biweekly, monthly）.
        attendees: 参加者リスト.
        next_occurrence: 次回開催日時.
        agent_id: 紐付けられたエージェントID（オプション）.
        created_at: 作成日時.
        updated_at: 更新日時.
    """

    id: UUID
    user_id: UUID
    google_event_id: str
    title: str
    rrule: str
    frequency: MeetingFrequency
    next_occurrence: datetime
    created_at: datetime
    attendees: list[Attendee] = field(default_factory=list)
    agent_id: UUID | None = None
    updated_at: datetime | None = None

    def link_agent(self, agent_id: UUID) -> None:
        """エージェントを紐付ける.

        Args:
            agent_id: 紐付けるエージェントのID.
        """
        self.agent_id = agent_id
        self.updated_at = datetime.now()

    def unlink_agent(self) -> None:
        """エージェントの紐付けを解除する."""
        self.agent_id = None
        self.updated_at = datetime.now()

    def is_linked(self) -> bool:
        """エージェントに紐付けられているか確認.

        Returns:
            True if linked to an agent, False otherwise.
        """
        return self.agent_id is not None

    def update_next_occurrence(self, next_date: datetime) -> None:
        """次回開催日時を更新する.

        Args:
            next_date: 次回の開催日時.
        """
        self.next_occurrence = next_date
        self.updated_at = datetime.now()
