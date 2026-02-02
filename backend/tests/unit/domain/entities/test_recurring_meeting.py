"""RecurringMeetingエンティティのユニットテスト."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.entities.recurring_meeting import RecurringMeeting


class TestRecurringMeeting:
    """RecurringMeetingエンティティのテスト."""

    def test_create_recurring_meeting(self) -> None:
        """定例MTGエンティティが正しく作成されることを確認."""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        created_at = datetime.now()
        next_occurrence = datetime(2026, 2, 10, 10, 0, 0)

        # Act
        meeting = RecurringMeeting(
            id=meeting_id,
            user_id=user_id,
            google_event_id="event_123",
            title="Weekly Standup",
            rrule="FREQ=WEEKLY;BYDAY=MO",
            frequency="weekly",
            next_occurrence=next_occurrence,
            created_at=created_at,
            attendees=["user1@example.com", "user2@example.com"],
        )

        # Assert
        assert meeting.id == meeting_id
        assert meeting.user_id == user_id
        assert meeting.google_event_id == "event_123"
        assert meeting.title == "Weekly Standup"
        assert meeting.rrule == "FREQ=WEEKLY;BYDAY=MO"
        assert meeting.frequency == "weekly"
        assert meeting.next_occurrence == next_occurrence
        assert meeting.created_at == created_at
        assert len(meeting.attendees) == 2
        assert meeting.agent_id is None
        assert meeting.updated_at is None

    def test_create_recurring_meeting_with_defaults(self) -> None:
        """デフォルト値で定例MTGエンティティが作成されることを確認."""
        # Arrange & Act
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="event_456",
            title="Monthly Review",
            rrule="FREQ=MONTHLY;BYMONTHDAY=1",
            frequency="monthly",
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
        )

        # Assert
        assert meeting.attendees == []
        assert meeting.agent_id is None
        assert meeting.updated_at is None

    def test_link_agent(self) -> None:
        """エージェント紐付けが正しく動作することを確認."""
        # Arrange
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="event_789",
            title="Sprint Planning",
            rrule="FREQ=WEEKLY;INTERVAL=2",
            frequency="biweekly",
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
        )
        agent_id = uuid4()

        # Act
        meeting.link_agent(agent_id)

        # Assert
        assert meeting.agent_id == agent_id
        assert meeting.updated_at is not None

    def test_unlink_agent(self) -> None:
        """エージェント紐付け解除が正しく動作することを確認."""
        # Arrange
        agent_id = uuid4()
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="event_abc",
            title="Team Sync",
            rrule="FREQ=WEEKLY",
            frequency="weekly",
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
            agent_id=agent_id,
        )

        # Act
        meeting.unlink_agent()

        # Assert
        assert meeting.agent_id is None
        assert meeting.updated_at is not None

    def test_update_next_occurrence(self) -> None:
        """次回開催日時更新が正しく動作することを確認."""
        # Arrange
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="event_def",
            title="Daily Standup",
            rrule="FREQ=DAILY",
            frequency="weekly",
            next_occurrence=datetime(2026, 2, 1, 9, 0, 0),
            created_at=datetime.now(),
        )
        new_occurrence = datetime(2026, 2, 8, 9, 0, 0)

        # Act
        meeting.update_next_occurrence(new_occurrence)

        # Assert
        assert meeting.next_occurrence == new_occurrence
        assert meeting.updated_at is not None

    def test_update_attendees(self) -> None:
        """参加者リスト更新が正しく動作することを確認."""
        # Arrange
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="event_ghi",
            title="Project Review",
            rrule="FREQ=MONTHLY",
            frequency="monthly",
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
            attendees=["old@example.com"],
        )
        new_attendees = ["new1@example.com", "new2@example.com", "new3@example.com"]

        # Act
        meeting.update_attendees(new_attendees)

        # Assert
        assert meeting.attendees == new_attendees
        assert len(meeting.attendees) == 3
        assert meeting.updated_at is not None

    @pytest.mark.parametrize(
        "frequency",
        ["weekly", "biweekly", "monthly"],
    )
    def test_valid_frequencies(self, frequency: str) -> None:
        """有効な頻度値でエンティティが作成されることを確認."""
        # Arrange & Act
        meeting = RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id=f"event_{frequency}",
            title=f"{frequency.capitalize()} Meeting",
            rrule="FREQ=WEEKLY",
            frequency=frequency,  # type: ignore[arg-type]
            next_occurrence=datetime.now(),
            created_at=datetime.now(),
        )

        # Assert
        assert meeting.frequency == frequency
