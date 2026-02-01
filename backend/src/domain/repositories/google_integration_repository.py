"""GoogleIntegrationRepository interface for domain layer.

Abstract base class defining the contract for Google integration persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.google_integration import GoogleIntegration


class GoogleIntegrationRepository(ABC):
    """Abstract repository interface for GoogleIntegration entity.

    This interface follows the Repository pattern from DDD,
    defining the contract for Google integration persistence operations.
    Concrete implementations are provided in the infrastructure layer.
    """

    @abstractmethod
    async def create(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Create a new Google integration.

        Args:
            integration: The GoogleIntegration entity to create.

        Returns:
            The created GoogleIntegration entity.
        """

    @abstractmethod
    async def get_by_id(self, integration_id: UUID, user_id: UUID) -> GoogleIntegration | None:
        """Retrieve a Google integration by ID.

        Args:
            integration_id: The unique identifier of the integration.
            user_id: The user ID for RLS filtering.

        Returns:
            The GoogleIntegration if found, None otherwise.
        """

    @abstractmethod
    async def get_by_email(
        self,
        user_id: UUID,
        email: str,
    ) -> GoogleIntegration | None:
        """Retrieve a Google integration by email.

        Args:
            user_id: The user ID.
            email: The Google account email address.

        Returns:
            The GoogleIntegration if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, user_id: UUID) -> list[GoogleIntegration]:
        """Retrieve all Google integrations for a user.

        Args:
            user_id: The user ID.

        Returns:
            A list of GoogleIntegration entities.
        """

    @abstractmethod
    async def update(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Update an existing Google integration.

        Args:
            integration: The GoogleIntegration entity with updated values.

        Returns:
            The updated GoogleIntegration entity.
        """

    @abstractmethod
    async def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Delete a Google integration.

        Args:
            integration_id: The unique identifier of the integration.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """
