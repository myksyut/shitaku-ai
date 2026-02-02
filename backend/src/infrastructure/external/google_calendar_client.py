"""Google Calendar API client for fetching recurring events.

Handles Calendar API access with RRULE parsing and filtering.
Following ADR-0003 authentication pattern.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Google Calendar API endpoint
CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"


@dataclass
class CalendarAttendee:
    """Calendar event attendee."""

    email: str
    display_name: str | None = None
    response_status: str | None = None


@dataclass
class CalendarEvent:
    """Google Calendar event with recurrence info."""

    event_id: str
    summary: str
    rrule: str
    attendees: list[CalendarAttendee]
    start_datetime: datetime
    organizer_email: str | None = None


class GoogleCalendarClient:
    """Google Calendar API client for fetching recurring events."""

    def __init__(self, access_token: str) -> None:
        """Initialize the Calendar client.

        Args:
            access_token: A valid Google OAuth access token with calendar.readonly scope.
        """
        self._access_token = access_token

    async def get_recurring_events(
        self,
        min_attendees: int = 2,
        months_back: int = 3,
    ) -> list[CalendarEvent]:
        """Fetch recurring events from Google Calendar.

        Filters:
        - Events with RRULE (recurrence rule)
        - At least min_attendees participants
        - Events that have occurred within months_back months

        Args:
            min_attendees: Minimum number of attendees required (default: 2).
            months_back: Only include events active within this many months (default: 3).

        Returns:
            List of CalendarEvent objects meeting the criteria.

        Raises:
            ValueError: If Calendar API request fails.
        """
        # Calculate time range
        now = datetime.now(UTC)
        time_min = now - timedelta(days=months_back * 30)
        time_max = now + timedelta(days=90)  # Look ahead 3 months for next occurrence

        events: list[CalendarEvent] = []

        async with httpx.AsyncClient() as client:
            # Fetch primary calendar events
            # singleEvents=false returns recurring event definitions with RRULE
            response = await client.get(
                f"{CALENDAR_API_URL}/calendars/primary/events",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "timeMin": time_min.isoformat(),
                    "timeMax": time_max.isoformat(),
                    "singleEvents": "false",  # Get recurring event definitions
                    "maxResults": 250,
                    "orderBy": "updated",
                },
            )

            if response.status_code == 401:
                raise ValueError("Google Calendar access token expired or invalid")

            if response.status_code != 200:
                error_msg = f"Google Calendar API error: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                raise ValueError(error_msg)

            data = response.json()
            items = data.get("items", [])

            for item in items:
                event = self._parse_event(item)
                if event is None:
                    continue

                # Filter: must have RRULE
                if not event.rrule:
                    continue

                # Filter: minimum attendees
                if len(event.attendees) < min_attendees:
                    continue

                events.append(event)

        logger.info(f"Found {len(events)} recurring events meeting criteria")
        return events

    def _parse_event(self, item: dict[str, Any]) -> CalendarEvent | None:
        """Parse a Calendar API event item into CalendarEvent.

        Args:
            item: Raw event data from Calendar API.

        Returns:
            CalendarEvent if valid, None if parsing fails.
        """
        try:
            event_id = item.get("id", "")
            summary = item.get("summary", "Untitled")

            # Extract RRULE from recurrence array
            recurrence = item.get("recurrence", [])
            rrule = ""
            for rule in recurrence:
                if rule.startswith("RRULE:"):
                    rrule = rule
                    break

            # Parse attendees
            attendees_raw = item.get("attendees", [])
            attendees: list[CalendarAttendee] = [
                CalendarAttendee(
                    email=a.get("email", ""),
                    display_name=a.get("displayName"),
                    response_status=a.get("responseStatus"),
                )
                for a in attendees_raw
            ]

            # Parse start datetime
            start_data = item.get("start", {})
            start_str = start_data.get("dateTime") or start_data.get("date")
            if not start_str:
                return None

            # Handle both datetime and date-only formats
            if "T" in start_str:
                # Full datetime with timezone
                start_datetime = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                # Date only - assume midnight UTC
                start_datetime = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=UTC)

            # Get organizer
            organizer = item.get("organizer", {})
            organizer_email = organizer.get("email")

            return CalendarEvent(
                event_id=event_id,
                summary=summary,
                rrule=rrule,
                attendees=attendees,
                start_datetime=start_datetime,
                organizer_email=organizer_email,
            )

        except Exception as e:
            logger.warning(f"Failed to parse calendar event: {e}")
            return None

    @staticmethod
    def parse_frequency_from_rrule(rrule: str) -> str:
        """Extract frequency from RRULE string.

        Args:
            rrule: iCalendar RRULE string (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO").

        Returns:
            Frequency string: "weekly", "biweekly", or "monthly".
        """
        rrule_upper = rrule.upper()

        if "FREQ=DAILY" in rrule_upper:
            return "weekly"  # Treat daily as weekly for simplicity

        if "FREQ=WEEKLY" in rrule_upper:
            # Check for INTERVAL=2 (biweekly)
            if "INTERVAL=2" in rrule_upper:
                return "biweekly"
            return "weekly"

        if "FREQ=MONTHLY" in rrule_upper:
            return "monthly"

        if "FREQ=YEARLY" in rrule_upper:
            return "monthly"  # Treat yearly as monthly for simplicity

        # Default to weekly
        return "weekly"

    @staticmethod
    def calculate_next_occurrence(rrule: str, start_datetime: datetime) -> datetime:
        """Calculate the next occurrence based on RRULE.

        This is a simplified implementation. For production, consider using
        dateutil.rrule for full RRULE support.

        Args:
            rrule: iCalendar RRULE string.
            start_datetime: The original start datetime of the event.

        Returns:
            The next occurrence datetime.
        """
        now = datetime.now(UTC)

        # If start is in the future, use it
        if start_datetime > now:
            return start_datetime

        frequency = GoogleCalendarClient.parse_frequency_from_rrule(rrule)

        # Simple calculation based on frequency
        if frequency == "weekly":
            days_since = (now - start_datetime).days
            weeks_passed = days_since // 7
            next_date = start_datetime + timedelta(weeks=weeks_passed + 1)
        elif frequency == "biweekly":
            days_since = (now - start_datetime).days
            biweeks_passed = days_since // 14
            next_date = start_datetime + timedelta(weeks=(biweeks_passed + 1) * 2)
        else:  # monthly
            # Simplified: add months by adding 30 days
            days_since = (now - start_datetime).days
            months_passed = days_since // 30
            next_date = start_datetime + timedelta(days=(months_passed + 1) * 30)

        return next_date
