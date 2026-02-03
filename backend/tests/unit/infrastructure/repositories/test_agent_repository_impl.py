"""Unit tests for AgentRepositoryImpl.

Tests for AgentRepositoryImpl focusing on reference settings mapping
(transcript_count, slack_message_days).
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.domain.entities.agent import Agent
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock Supabase client fixture."""
    return MagicMock()


class TestAgentRepositoryImplReferenceSettings:
    """Reference settings related tests."""

    def test_to_entity_with_reference_settings(self) -> None:
        """Reference settings fields are converted to entity correctly."""
        # Arrange
        row = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test Agent",
            "description": "Test Description",
            "slack_channel_id": "C123456",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "transcript_count": 5,
            "slack_message_days": 14,
        }

        # Act
        agent = AgentRepositoryImpl._to_entity(AgentRepositoryImpl(MagicMock()), row)

        # Assert
        assert agent.transcript_count == 5
        assert agent.slack_message_days == 14

    def test_to_entity_with_default_reference_settings(self) -> None:
        """Default values are used when reference settings are missing."""
        # Arrange
        row = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test Agent",
            "description": None,
            "slack_channel_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            # transcript_count, slack_message_days are missing
        }

        # Act
        agent = AgentRepositoryImpl._to_entity(AgentRepositoryImpl(MagicMock()), row)

        # Assert
        assert agent.transcript_count == 3  # Default value
        assert agent.slack_message_days == 7  # Default value

    def test_to_entity_with_null_reference_settings(self) -> None:
        """Default values are used when reference settings are NULL."""
        # Arrange
        row = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test Agent",
            "description": None,
            "slack_channel_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "transcript_count": None,  # NULL from DB
            "slack_message_days": None,  # NULL from DB
        }

        # Act
        agent = AgentRepositoryImpl._to_entity(AgentRepositoryImpl(MagicMock()), row)

        # Assert
        assert agent.transcript_count == 3  # Default value
        assert agent.slack_message_days == 7  # Default value

    def test_create_with_reference_settings(self, mock_client: MagicMock) -> None:
        """Agent with reference settings can be created."""
        # Arrange
        repo = AgentRepositoryImpl(mock_client)
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
            transcript_count=8,
            slack_message_days=21,
        )

        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(agent.id),
                    "user_id": str(agent.user_id),
                    "name": agent.name,
                    "description": None,
                    "slack_channel_id": None,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": None,
                    "transcript_count": 8,
                    "slack_message_days": 21,
                }
            ]
        )

        # Act
        repo.create(agent)

        # Assert
        insert_call = mock_client.table.return_value.insert.call_args
        insert_data = insert_call[0][0]
        assert insert_data["transcript_count"] == 8
        assert insert_data["slack_message_days"] == 21

    def test_create_with_default_reference_settings(self, mock_client: MagicMock) -> None:
        """Agent with default reference settings uses defaults in insert."""
        # Arrange
        repo = AgentRepositoryImpl(mock_client)
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
            # Using default values
        )

        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(agent.id),
                    "user_id": str(agent.user_id),
                    "name": agent.name,
                    "description": None,
                    "slack_channel_id": None,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": None,
                    "transcript_count": 3,
                    "slack_message_days": 7,
                }
            ]
        )

        # Act
        repo.create(agent)

        # Assert
        insert_call = mock_client.table.return_value.insert.call_args
        insert_data = insert_call[0][0]
        assert insert_data["transcript_count"] == 3  # Default
        assert insert_data["slack_message_days"] == 7  # Default

    def test_update_with_reference_settings(self, mock_client: MagicMock) -> None:
        """Reference settings can be updated."""
        # Arrange
        repo = AgentRepositoryImpl(mock_client)
        agent = Agent(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Agent",
            created_at=datetime.now(),
            transcript_count=10,
            slack_message_days=30,
        )

        update_chain = mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value
        update_chain.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(agent.id),
                    "user_id": str(agent.user_id),
                    "name": agent.name,
                    "description": None,
                    "slack_channel_id": None,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "transcript_count": 10,
                    "slack_message_days": 30,
                }
            ]
        )

        # Act
        repo.update(agent)

        # Assert
        update_call = mock_client.table.return_value.update.call_args
        update_data = update_call[0][0]
        assert update_data["transcript_count"] == 10
        assert update_data["slack_message_days"] == 30
