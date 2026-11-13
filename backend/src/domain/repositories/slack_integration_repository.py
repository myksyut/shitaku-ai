from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.slack_integration import SlackIntegration


class SlackIntegrationRepository(ABC):
    """Owner-scoped Slack integration persistence."""

    @abstractmethod
    async def create(self, integration: SlackIntegration) -> SlackIntegration:
        """Create a personal integration."""

    @abstractmethod
    async def get_by_id(self, integration_id: UUID, user_id: UUID) -> SlackIntegration | None:
        """Read one selected owned integration."""

    @abstractmethod
    async def get_by_workspace(self, user_id: UUID, workspace_id: str) -> SlackIntegration | None:
        """Find a user's workspace binding."""

    @abstractmethod
    async def get_all(self, user_id: UUID) -> list[SlackIntegration]:
        """List personal integrations."""

    @abstractmethod
    async def update(self, integration: SlackIntegration) -> SlackIntegration:
        """Update an owned integration."""

    @abstractmethod
    async def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Disconnect an owned integration."""
