"""Tests for Knowledge entity."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.knowledge import Knowledge


class TestKnowledge:
    """Knowledgeエンティティのテスト."""

    def test_knowledge_creation(self) -> None:
        """Knowledgeが正しくインスタンス化できること."""
        knowledge_id = uuid4()
        agent_id = uuid4()
        user_id = uuid4()
        original_text = "かなざわさんが発言しました"
        normalized_text = "金沢太郎さんが発言しました"
        meeting_date = datetime(2026, 1, 15, 10, 0, 0)
        created_at = datetime.now()

        knowledge = Knowledge(
            id=knowledge_id,
            agent_id=agent_id,
            user_id=user_id,
            original_text=original_text,
            normalized_text=normalized_text,
            meeting_date=meeting_date,
            created_at=created_at,
        )

        assert knowledge.id == knowledge_id
        assert knowledge.agent_id == agent_id
        assert knowledge.user_id == user_id
        assert knowledge.original_text == original_text
        assert knowledge.normalized_text == normalized_text
        assert knowledge.meeting_date == meeting_date
        assert knowledge.created_at == created_at
        assert knowledge.updated_at is None

    def test_update_normalized_text(self) -> None:
        """正規化後テキストを更新できること."""
        knowledge = Knowledge(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="元のテキスト",
            normalized_text="元のテキスト",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert knowledge.updated_at is None

        new_normalized_text = "正規化後のテキスト"
        knowledge.update_normalized_text(new_normalized_text)

        assert knowledge.normalized_text == new_normalized_text
        assert knowledge.updated_at is not None

    def test_is_normalized_returns_true_when_text_changed(self) -> None:
        """正規化でテキストが変更された場合はTrueを返すこと."""
        knowledge = Knowledge(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="かなざわさん",
            normalized_text="金沢太郎さん",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert knowledge.is_normalized() is True

    def test_is_normalized_returns_false_when_text_unchanged(self) -> None:
        """正規化でテキストが変更されなかった場合はFalseを返すこと."""
        same_text = "変更なしのテキスト"
        knowledge = Knowledge(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text=same_text,
            normalized_text=same_text,
            meeting_date=datetime.now(),
            created_at=datetime.now(),
        )

        assert knowledge.is_normalized() is False

    def test_knowledge_with_updated_at(self) -> None:
        """updated_atを指定してインスタンス化できること."""
        updated_at = datetime.now()
        knowledge = Knowledge(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            original_text="テキスト",
            normalized_text="テキスト",
            meeting_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=updated_at,
        )

        assert knowledge.updated_at == updated_at
