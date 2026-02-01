"""Tests for MeetingNote entity."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.meeting_note import MeetingNote


class TestMeetingNote:
    """MeetingNoteエンティティのテスト."""

    def test_meeting_note_creation(self) -> None:
        """MeetingNoteが正しくインスタンス化できること."""
        note_id = uuid4()
        agent_id = uuid4()
        user_id = uuid4()
        original_text = "かなざわさんが発言しました"
        normalized_text = "金沢太郎さんが発言しました"
        meeting_date = datetime(2026, 1, 15, 10, 0, 0)
        created_at = datetime.now()

        note = MeetingNote(
            id=note_id,
            agent_id=agent_id,
            user_id=user_id,
            original_text=original_text,
            normalized_text=normalized_text,
            meeting_date=meeting_date,
            created_at=created_at,
        )

        assert note.id == note_id
        assert note.agent_id == agent_id
        assert note.user_id == user_id
        assert note.original_text == original_text
        assert note.normalized_text == normalized_text
        assert note.meeting_date == meeting_date
        assert note.created_at == created_at
        assert note.updated_at is None

    def test_update_normalized_text(self) -> None:
        """正規化後テキストを更新できること."""
        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="元のテキスト",
            normalized_text="元のテキスト",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert note.updated_at is None

        new_normalized_text = "正規化後のテキスト"
        note.update_normalized_text(new_normalized_text)

        assert note.normalized_text == new_normalized_text
        assert note.updated_at is not None

    def test_is_normalized_returns_true_when_text_changed(self) -> None:
        """正規化でテキストが変更された場合はTrueを返すこと."""
        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="かなざわさん",
            normalized_text="金沢太郎さん",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert note.is_normalized() is True

    def test_is_normalized_returns_false_when_text_unchanged(self) -> None:
        """正規化でテキストが変更されなかった場合はFalseを返すこと."""
        same_text = "変更なしのテキスト"
        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text=same_text,
            normalized_text=same_text,
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert note.is_normalized() is False

    def test_meeting_note_with_updated_at(self) -> None:
        """updated_atを指定してインスタンス化できること."""
        updated_at = datetime.now()
        note = MeetingNote(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="テキスト",
            normalized_text="テキスト",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=updated_at,
        )

        assert note.updated_at == updated_at
