"""RecurringMeetingRepository interface for domain layer.

Abstract base class defining the contract for recurring meeting persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.recurring_meeting import RecurringMeeting


class RecurringMeetingRepository(ABC):
    """Abstract repository interface for RecurringMeeting entity.

    This interface follows the Repository pattern from DDD,
    defining the contract for recurring meeting persistence operations.
    Concrete implementations are provided in the infrastructure layer.
    """

    @abstractmethod
    async def create(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """Create a new recurring meeting.

        Args:
            meeting: The RecurringMeeting entity to create.

        Returns:
            The created RecurringMeeting entity.
        """

    @abstractmethod
    async def get_by_id(self, meeting_id: UUID, user_id: UUID) -> RecurringMeeting | None:
        """Retrieve a recurring meeting by ID.

        Args:
            meeting_id: The unique identifier of the meeting.
            user_id: The user ID for RLS filtering.

        Returns:
            The RecurringMeeting if found, None otherwise.
        """

    @abstractmethod
    async def get_by_google_event_id(
        self,
        user_id: UUID,
        google_event_id: str,
    ) -> RecurringMeeting | None:
        """Retrieve a recurring meeting by Google event ID.

        Args:
            user_id: The user ID.
            google_event_id: The Google Calendar event ID.

        Returns:
            The RecurringMeeting if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, user_id: UUID) -> list[RecurringMeeting]:
        """Retrieve all recurring meetings for a user.

        Args:
            user_id: The user ID.

        Returns:
            A list of RecurringMeeting entities.
        """

    @abstractmethod
    async def get_list_by_agent_id(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> list[RecurringMeeting]:
        """Retrieve recurring meetings linked to an agent (1-to-many support).

        Args:
            agent_id: The agent ID.
            user_id: The user ID for RLS filtering.

        Returns:
            List of RecurringMeeting entities linked to the agent.
        """

    @abstractmethod
    async def link_to_agent(
        self,
        recurring_meeting_id: UUID,
        agent_id: UUID,
        user_id: UUID,
    ) -> RecurringMeeting:
        """Link a recurring meeting to an agent.

        Args:
            recurring_meeting_id: The recurring meeting ID.
            agent_id: The agent ID to link.
            user_id: The user ID for RLS filtering.

        Returns:
            The updated RecurringMeeting entity.

        Raises:
            ValueError: If meeting not found or access denied.
        """

    @abstractmethod
    async def unlink_from_agent(
        self,
        recurring_meeting_id: UUID,
        user_id: UUID,
    ) -> None:
        """Unlink a recurring meeting from an agent.

        Args:
            recurring_meeting_id: The recurring meeting ID.
            user_id: The user ID for RLS filtering.
        """

    @abstractmethod
    async def get_unlinked(self, user_id: UUID) -> list[RecurringMeeting]:
        """Retrieve all recurring meetings not linked to any agent.

        Args:
            user_id: The user ID.

        Returns:
            A list of unlinked RecurringMeeting entities.
        """

    @abstractmethod
    async def update(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """Update an existing recurring meeting.

        Args:
            meeting: The RecurringMeeting entity with updated values.

        Returns:
            The updated RecurringMeeting entity.
        """

    @abstractmethod
    async def delete(self, meeting_id: UUID, user_id: UUID) -> bool:
        """Delete a recurring meeting.

        Args:
            meeting_id: The unique identifier of the meeting.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    async def upsert(self, meeting: RecurringMeeting) -> RecurringMeeting:
        """Create or update a recurring meeting based on google_event_id.

        If a meeting with the same user_id and google_event_id exists,
        update it. Otherwise, create a new one.

        Args:
            meeting: The RecurringMeeting entity to upsert.

        Returns:
            The created or updated RecurringMeeting entity.
        """
