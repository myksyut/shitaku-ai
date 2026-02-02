"""Calendar use cases for recurring meeting management.

Application layer use cases for syncing and managing recurring meetings.
Following ADR-0001 clean architecture principles.
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.recurring_meeting import (
    Attendee,
    MeetingFrequency,
    RecurringMeeting,
)
from src.domain.repositories.google_integration_repository import (
    GoogleIntegrationRepository,
)
from src.domain.repositories.recurring_meeting_repository import (
    RecurringMeetingRepository,
)
from src.infrastructure.external.encryption import decrypt_google_token
from src.infrastructure.external.google_calendar_client import (
    GoogleCalendarClient,
)
from src.infrastructure.external.google_oauth_client import GoogleOAuthClient

logger = logging.getLogger(__name__)


class SyncRecurringMeetingsUseCase:
    """Sync recurring meetings from Google Calendar.

    This use case fetches recurring events from Google Calendar
    and upserts them into the database.
    """

    def __init__(
        self,
        google_integration_repo: GoogleIntegrationRepository,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            google_integration_repo: Repository for Google integrations.
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._google_integration_repo = google_integration_repo
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(self, user_id: UUID) -> list[RecurringMeeting]:
        """Sync recurring meetings from Google Calendar.

        Args:
            user_id: The user ID to sync meetings for.

        Returns:
            List of synced RecurringMeeting entities.

        Raises:
            ValueError: If no Google integration found or sync fails.
        """
        # Get Google integrations for user
        integrations = await self._google_integration_repo.get_all(user_id)
        if not integrations:
            raise ValueError("No Google integration found. Please connect Google first.")

        # Use the first integration (primary account)
        integration = integrations[0]

        # Check if calendar scope is available
        calendar_scope = "https://www.googleapis.com/auth/calendar.readonly"
        if not integration.has_scope(calendar_scope):
            raise ValueError("Calendar scope not granted. Please reconnect Google.")

        # Decrypt refresh token and get new access token
        try:
            refresh_token = decrypt_google_token(integration.encrypted_refresh_token)
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise ValueError("Failed to decrypt Google token. Please reconnect.") from None

        # Get fresh access token
        oauth_client = GoogleOAuthClient()
        try:
            token_response = await oauth_client.refresh_access_token(refresh_token)
        except ValueError as e:
            logger.error(f"Failed to refresh token: {e}")
            raise ValueError("Failed to refresh Google token. Please reconnect.") from None

        # Fetch recurring events from Calendar
        calendar_client = GoogleCalendarClient(token_response.access_token)
        try:
            events = await calendar_client.get_recurring_events(
                min_attendees=2,
                months_back=3,
            )
        except ValueError as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            raise

        # Convert and upsert meetings
        synced_meetings: list[RecurringMeeting] = []
        for event in events:
            # Parse frequency from RRULE
            frequency_str = GoogleCalendarClient.parse_frequency_from_rrule(event.rrule)
            try:
                frequency = MeetingFrequency(frequency_str)
            except ValueError:
                frequency = MeetingFrequency.WEEKLY

            # Calculate next occurrence
            next_occurrence = GoogleCalendarClient.calculate_next_occurrence(event.rrule, event.start_datetime)

            # Convert attendees
            attendees = [Attendee(email=a.email, name=a.display_name) for a in event.attendees]

            # Check if meeting already exists
            existing = await self._recurring_meeting_repo.get_by_google_event_id(user_id, event.event_id)

            meeting = RecurringMeeting(
                id=existing.id if existing else uuid4(),
                user_id=user_id,
                google_event_id=event.event_id,
                title=event.summary,
                rrule=event.rrule,
                frequency=frequency,
                attendees=attendees,
                next_occurrence=next_occurrence,
                agent_id=existing.agent_id if existing else None,
                created_at=existing.created_at if existing else datetime.now(),
                updated_at=datetime.now() if existing else None,
            )

            synced_meeting = await self._recurring_meeting_repo.upsert(meeting)
            synced_meetings.append(synced_meeting)

        logger.info(f"Synced {len(synced_meetings)} recurring meetings for user {user_id}")
        return synced_meetings


class GetRecurringMeetingsUseCase:
    """Get all recurring meetings for a user."""

    def __init__(
        self,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(self, user_id: UUID) -> list[RecurringMeeting]:
        """Get all recurring meetings for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of RecurringMeeting entities.
        """
        return await self._recurring_meeting_repo.get_all(user_id)


class GetUnlinkedMeetingsUseCase:
    """Get recurring meetings not linked to any agent."""

    def __init__(
        self,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(self, user_id: UUID) -> list[RecurringMeeting]:
        """Get unlinked recurring meetings.

        Args:
            user_id: The user ID.

        Returns:
            List of unlinked RecurringMeeting entities.
        """
        return await self._recurring_meeting_repo.get_unlinked(user_id)


class LinkAgentToMeetingUseCase:
    """Link an agent to a recurring meeting."""

    def __init__(
        self,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(
        self,
        meeting_id: UUID,
        agent_id: UUID,
        user_id: UUID,
    ) -> RecurringMeeting:
        """Link an agent to a recurring meeting.

        Args:
            meeting_id: The recurring meeting ID.
            agent_id: The agent ID to link.
            user_id: The user ID for authorization.

        Returns:
            The updated RecurringMeeting entity.

        Raises:
            ValueError: If meeting not found.
        """
        return await self._recurring_meeting_repo.link_to_agent(meeting_id, agent_id, user_id)


class UnlinkAgentFromMeetingUseCase:
    """Unlink an agent from a recurring meeting."""

    def __init__(
        self,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(
        self,
        meeting_id: UUID,
        user_id: UUID,
    ) -> None:
        """Unlink an agent from a recurring meeting.

        Args:
            meeting_id: The recurring meeting ID.
            user_id: The user ID for authorization.
        """
        await self._recurring_meeting_repo.unlink_from_agent(meeting_id, user_id)


class GetMeetingsByAgentUseCase:
    """Get the recurring meetings linked to an agent (1-to-many support)."""

    def __init__(
        self,
        recurring_meeting_repo: RecurringMeetingRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            recurring_meeting_repo: Repository for recurring meetings.
        """
        self._recurring_meeting_repo = recurring_meeting_repo

    async def execute(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> list[RecurringMeeting]:
        """Get the recurring meetings linked to an agent.

        Args:
            agent_id: The agent ID.
            user_id: The user ID for authorization.

        Returns:
            List of linked RecurringMeeting entities.
        """
        return await self._recurring_meeting_repo.get_list_by_agent_id(agent_id, user_id)
