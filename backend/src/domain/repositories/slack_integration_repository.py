"""SlackIntegrationRepository interface for domain layer.

Abstract base class defining the contract for Slack integration persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.slack_integration import SlackIntegration, SlackMessage


class SlackIntegrationRepository(ABC):
    """Abstract repository interface for SlackIntegration entity.

    This interface follows the Repository pattern from DDD,
    defining the contract for Slack integration persistence operations.
    Concrete implementations are provided in the infrastructure layer.
    """

    @abstractmethod
    async def create(self, integration: SlackIntegration) -> SlackIntegration:
        """Create a new Slack integration.

        Args:
            integration: The SlackIntegration entity to create.

        Returns:
            The created SlackIntegration entity.
        """

    @abstractmethod
    async def get_by_id(self, integration_id: UUID, user_id: UUID) -> SlackIntegration | None:
        """Retrieve a Slack integration by ID.

        Args:
            integration_id: The unique identifier of the integration.
            user_id: The user ID for RLS filtering.

        Returns:
            The SlackIntegration if found, None otherwise.
        """

    @abstractmethod
    async def get_by_workspace(
        self,
        user_id: UUID,
        workspace_id: str,
    ) -> SlackIntegration | None:
        """Retrieve a Slack integration by workspace ID.

        Args:
            user_id: The user ID.
            workspace_id: The Slack workspace ID.

        Returns:
            The SlackIntegration if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, user_id: UUID) -> list[SlackIntegration]:
        """Retrieve all Slack integrations for a user.

        Args:
            user_id: The user ID.

        Returns:
            A list of SlackIntegration entities.
        """

    @abstractmethod
    async def update(self, integration: SlackIntegration) -> SlackIntegration:
        """Update an existing Slack integration.

        Args:
            integration: The SlackIntegration entity with updated values.

        Returns:
            The updated SlackIntegration entity.
        """

    @abstractmethod
    async def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Delete a Slack integration.

        Args:
            integration_id: The unique identifier of the integration.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    async def save_messages(self, messages: list[SlackMessage]) -> None:
        """Save Slack messages.

        Args:
            messages: The list of SlackMessage entities to save.
        """

    @abstractmethod
    async def get_messages_by_channel(
        self,
        integration_id: UUID,
        channel_id: str,
        after: datetime,
        before: datetime | None = None,
    ) -> list[SlackMessage]:
        """Retrieve Slack messages by channel within a time range.

        Args:
            integration_id: The Slack integration ID.
            channel_id: The Slack channel ID.
            after: Start of the time range (inclusive).
            before: End of the time range (exclusive). None means now.

        Returns:
            A list of SlackMessage entities.
        """
