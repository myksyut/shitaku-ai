"""Unit tests for Agent entity.

Tests for Agent domain entity following TDD Red-Green-Refactor process.
"""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.agent import Agent


class TestAgentCreation:
    """Test Agent entity instantiation."""

    def test_agent_creation_with_required_fields(self) -> None:
        """Agentが必須フィールドで正しくインスタンス化できる"""
        # Arrange
        agent_id = uuid4()
        user_id = uuid4()
        name = "週次定例MTG"
        created_at = datetime.now()

        # Act
        agent = Agent(
            id=agent_id,
            user_id=user_id,
            name=name,
            created_at=created_at,
        )

        # Assert
        assert agent.id == agent_id
        assert agent.user_id == user_id
        assert agent.name == name
        assert agent.description is None
        assert agent.slack_channel_id is None
        assert agent.created_at == created_at
        assert agent.updated_at is None

    def test_agent_creation_with_all_fields(self) -> None:
        """Agentが全フィールドで正しくインスタンス化できる"""
        # Arrange
        agent_id = uuid4()
        user_id = uuid4()
        name = "プロダクトチーム定例"
        description = "毎週月曜日のプロダクトチーム定例MTG"
        slack_channel_id = "C0123456789"
        created_at = datetime.now()
        updated_at = datetime.now()

        # Act
        agent = Agent(
            id=agent_id,
            user_id=user_id,
            name=name,
            description=description,
            slack_channel_id=slack_channel_id,
            created_at=created_at,
            updated_at=updated_at,
        )

        # Assert
        assert agent.id == agent_id
        assert agent.user_id == user_id
        assert agent.name == name
        assert agent.description == description
        assert agent.slack_channel_id == slack_channel_id
        assert agent.created_at == created_at
        assert agent.updated_at == updated_at


class TestAgentUpdateSlackChannel:
    """Test Agent.update_slack_channel method."""

    def test_update_slack_channel_sets_channel_id(self) -> None:
        """update_slack_channelがチャンネルIDを正しく設定する"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="テストMTG",
            created_at=datetime.now(),
        )
        channel_id = "C9876543210"

        # Act
        agent.update_slack_channel(channel_id)

        # Assert
        assert agent.slack_channel_id == channel_id
        assert agent.updated_at is not None

    def test_update_slack_channel_with_none_clears_channel(self) -> None:
        """update_slack_channelにNoneを渡すとチャンネルIDがクリアされる"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="テストMTG",
            slack_channel_id="C0123456789",
            created_at=datetime.now(),
        )

        # Act
        agent.update_slack_channel(None)

        # Assert
        assert agent.slack_channel_id is None
        assert agent.updated_at is not None


class TestAgentUpdateInfo:
    """Test Agent.update_info method."""

    def test_update_info_updates_name(self) -> None:
        """update_infoが名前を正しく更新する"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="旧MTG名",
            created_at=datetime.now(),
        )

        # Act
        agent.update_info(name="新MTG名")

        # Assert
        assert agent.name == "新MTG名"
        assert agent.updated_at is not None

    def test_update_info_updates_description(self) -> None:
        """update_infoが説明を正しく更新する"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="テストMTG",
            created_at=datetime.now(),
        )

        # Act
        agent.update_info(description="新しい説明文")

        # Assert
        assert agent.description == "新しい説明文"
        assert agent.updated_at is not None

    def test_update_info_updates_both_name_and_description(self) -> None:
        """update_infoが名前と説明の両方を同時に更新する"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="旧MTG名",
            description="旧説明",
            created_at=datetime.now(),
        )

        # Act
        agent.update_info(name="新MTG名", description="新説明")

        # Assert
        assert agent.name == "新MTG名"
        assert agent.description == "新説明"
        assert agent.updated_at is not None

    def test_update_info_with_none_does_not_change_existing_values(self) -> None:
        """update_infoにNoneを渡しても既存の値は変更されない"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="テストMTG",
            description="テスト説明",
            created_at=datetime.now(),
        )
        original_name = agent.name
        original_description = agent.description

        # Act
        agent.update_info(name=None, description=None)

        # Assert
        assert agent.name == original_name
        assert agent.description == original_description


class TestAgentReferenceSettings:
    """Test Agent reference settings (transcript_count, slack_message_days)."""

    def test_default_values(self) -> None:
        """デフォルト値が設定されていること"""
        # Arrange & Act
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )

        # Assert
        assert agent.transcript_count == 3
        assert agent.slack_message_days == 7

    def test_update_reference_settings_valid(self) -> None:
        """有効な値で参照設定を更新できること"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )
        original_updated_at = agent.updated_at

        # Act
        agent.update_reference_settings(transcript_count=5, slack_message_days=14)

        # Assert
        assert agent.transcript_count == 5
        assert agent.slack_message_days == 14
        assert agent.updated_at != original_updated_at

    def test_update_reference_settings_partial(self) -> None:
        """一部の設定のみ更新できること"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )

        # Act
        agent.update_reference_settings(transcript_count=10)

        # Assert
        assert agent.transcript_count == 10
        assert agent.slack_message_days == 7  # デフォルトのまま

    def test_update_reference_settings_transcript_count_out_of_range(self) -> None:
        """transcript_countが範囲外の場合はValueError"""
        import pytest

        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="transcript_count must be between 0 and 10"):
            agent.update_reference_settings(transcript_count=11)

        with pytest.raises(ValueError, match="transcript_count must be between 0 and 10"):
            agent.update_reference_settings(transcript_count=-1)

    def test_update_reference_settings_slack_message_days_out_of_range(self) -> None:
        """slack_message_daysが範囲外の場合はValueError"""
        import pytest

        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="slack_message_days must be between 1 and 30"):
            agent.update_reference_settings(slack_message_days=0)

        with pytest.raises(ValueError, match="slack_message_days must be between 1 and 30"):
            agent.update_reference_settings(slack_message_days=31)

    def test_update_reference_settings_boundary_values(self) -> None:
        """境界値で更新できること"""
        # Arrange
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
        )

        # Act - 最小値
        agent.update_reference_settings(transcript_count=0, slack_message_days=1)

        # Assert
        assert agent.transcript_count == 0
        assert agent.slack_message_days == 1

        # Act - 最大値
        agent.update_reference_settings(transcript_count=10, slack_message_days=30)

        # Assert
        assert agent.transcript_count == 10
        assert agent.slack_message_days == 30
