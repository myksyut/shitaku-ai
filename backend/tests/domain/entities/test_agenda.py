"""Unit tests for Agenda entity.

Tests for Agenda domain entity following TDD Red-Green-Refactor process.
"""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.agenda import Agenda


class TestAgendaCreation:
    """Test Agenda entity instantiation."""

    def test_agenda_creation_with_required_fields(self) -> None:
        """Agendaが必須フィールドで正しくインスタンス化できる"""
        # Arrange
        agenda_id = uuid4()
        agent_id = uuid4()
        user_id = uuid4()
        content = "## 次回MTGアジェンダ\n\n### 1. 進捗確認"
        generated_at = datetime.now()
        created_at = datetime.now()

        # Act
        agenda = Agenda(
            id=agenda_id,
            agent_id=agent_id,
            user_id=user_id,
            content=content,
            generated_at=generated_at,
            created_at=created_at,
        )

        # Assert
        assert agenda.id == agenda_id
        assert agenda.agent_id == agent_id
        assert agenda.user_id == user_id
        assert agenda.content == content
        assert agenda.source_knowledge_id is None
        assert agenda.generated_at == generated_at
        assert agenda.created_at == created_at
        assert agenda.updated_at is None

    def test_agenda_creation_with_all_fields(self) -> None:
        """Agendaが全フィールドで正しくインスタンス化できる"""
        # Arrange
        agenda_id = uuid4()
        agent_id = uuid4()
        user_id = uuid4()
        source_knowledge_id = uuid4()
        content = "## 次回MTGアジェンダ\n\n### 1. 進捗確認\n### 2. 課題共有"
        generated_at = datetime.now()
        created_at = datetime.now()
        updated_at = datetime.now()

        # Act
        agenda = Agenda(
            id=agenda_id,
            agent_id=agent_id,
            user_id=user_id,
            content=content,
            source_knowledge_id=source_knowledge_id,
            generated_at=generated_at,
            created_at=created_at,
            updated_at=updated_at,
        )

        # Assert
        assert agenda.id == agenda_id
        assert agenda.agent_id == agent_id
        assert agenda.user_id == user_id
        assert agenda.content == content
        assert agenda.source_knowledge_id == source_knowledge_id
        assert agenda.generated_at == generated_at
        assert agenda.created_at == created_at
        assert agenda.updated_at == updated_at


class TestAgendaUpdateContent:
    """Test Agenda.update_content method."""

    def test_update_content_updates_content_and_updated_at(self) -> None:
        """update_contentがcontentとupdated_atを正しく更新する"""
        # Arrange
        agenda = Agenda(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            content="元のアジェンダ内容",
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )
        new_content = "更新後のアジェンダ内容"

        # Act
        agenda.update_content(new_content)

        # Assert
        assert agenda.content == new_content
        assert agenda.updated_at is not None

    def test_update_content_with_empty_string(self) -> None:
        """update_contentに空文字を渡しても更新される"""
        # Arrange
        agenda = Agenda(
            id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            content="元のアジェンダ内容",
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )

        # Act
        agenda.update_content("")

        # Assert
        assert agenda.content == ""
        assert agenda.updated_at is not None
