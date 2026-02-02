"""Google Calendar API client for fetching calendar events.

Handles calendar event retrieval with support for recurring events.
Following ADR-0003 authentication pattern and existing google_oauth_client.py patterns.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import cast

import httpx


@dataclass
class CalendarAttendee:
    """Calendar event attendee."""

    email: str
    display_name: str | None = None
    response_status: str | None = None
    is_organizer: bool = False


@dataclass
class CalendarOrganizer:
    """Calendar event organizer."""

    email: str
    display_name: str | None = None
    is_self: bool = False


@dataclass
class CalendarEvent:
    """Calendar event with recurrence information."""

    id: str
    summary: str
    start: datetime
    end: datetime
    recurrence: list[str] | None = None
    attendees: list[CalendarAttendee] | None = None
    organizer: CalendarOrganizer | None = None


class GoogleCalendarClient:
    """Google Calendar API client.

    Fetches calendar events with support for recurring events.
    Includes rate limit handling with Exponential Backoff.
    """

    BASE_URL = "https://www.googleapis.com/calendar/v3"
    MAX_RETRIES = 5

    def __init__(self, access_token: str) -> None:
        """Initialize the Google Calendar client.

        Args:
            access_token: Google API access token.
        """
        self._access_token = access_token

    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 250,
    ) -> list[CalendarEvent]:
        """Fetch calendar events with recurrence information.

        Uses singleEvents=false to get recurring event masters.

        Args:
            calendar_id: Calendar ID (default: primary).
            time_min: Start datetime for filtering.
            time_max: End datetime for filtering.
            max_results: Maximum number of results per page.

        Returns:
            List of CalendarEvent with recurrence information.

        Raises:
            ValueError: If API call fails.
        """
        params = self._build_params(time_min, time_max, max_results)
        events: list[CalendarEvent] = []

        async with httpx.AsyncClient() as client:
            page_token: str | None = None
            while True:
                if page_token:
                    params["pageToken"] = page_token

                data = await self._fetch_events_page(client, calendar_id, params)
                events.extend(self._extract_recurring_events(data))

                next_token = data.get("nextPageToken")
                if not isinstance(next_token, str):
                    break
                page_token = next_token

        return events

    def _build_params(
        self,
        time_min: datetime | None,
        time_max: datetime | None,
        max_results: int,
    ) -> dict[str, str | int]:
        """Build query parameters for events API.

        Args:
            time_min: Start datetime for filtering.
            time_max: End datetime for filtering.
            max_results: Maximum number of results per page.

        Returns:
            Query parameters dictionary.
        """
        params: dict[str, str | int] = {
            "singleEvents": "false",
            "maxResults": max_results,
        }

        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        if time_max:
            params["timeMax"] = time_max.isoformat() + "Z"

        return params

    async def _fetch_events_page(
        self,
        client: httpx.AsyncClient,
        calendar_id: str,
        params: dict[str, str | int],
    ) -> dict[str, object]:
        """Fetch a single page of events with retry logic.

        Args:
            client: HTTP client instance.
            calendar_id: Calendar ID.
            params: Query parameters.

        Returns:
            API response data.

        Raises:
            ValueError: If API call fails after retries.
        """
        retry_count = 0

        while True:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/calendars/{calendar_id}/events",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    params=params,
                )

                if response.status_code == 429:
                    if retry_count >= self.MAX_RETRIES:
                        raise ValueError("Rate limit exceeded after max retries")
                    wait_time = 2**retry_count
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue

                if response.status_code != 200:
                    raise ValueError(f"Calendar API error: {response.text}")

                return cast(dict[str, object], response.json())

            except httpx.RequestError as e:
                raise ValueError(f"Calendar API request failed: {e!s}") from e

    def _extract_recurring_events(self, data: dict[str, object]) -> list[CalendarEvent]:
        """Extract recurring events from API response.

        Args:
            data: API response data.

        Returns:
            List of parsed CalendarEvent objects.
        """
        events: list[CalendarEvent] = []
        items = data.get("items", [])

        if not isinstance(items, list):
            return events

        for item in items:
            if not isinstance(item, dict) or "recurrence" not in item:
                continue

            event = self._parse_event(item)
            if event:
                events.append(event)

        return events

    def _parse_event(self, item: dict[str, object]) -> CalendarEvent | None:
        """Parse API response item into CalendarEvent.

        Args:
            item: Raw event data from Google Calendar API.

        Returns:
            CalendarEvent or None if parsing fails.
        """
        try:
            start_data = item.get("start", {})
            end_data = item.get("end", {})

            if not isinstance(start_data, dict) or not isinstance(end_data, dict):
                return None

            start_str = start_data.get("dateTime") or start_data.get("date")
            end_str = end_data.get("dateTime") or end_data.get("date")

            if not isinstance(start_str, str) or not isinstance(end_str, str):
                return None

            start = self._parse_datetime(start_str)
            end = self._parse_datetime(end_str)

            event_id = item.get("id")
            if not isinstance(event_id, str):
                return None

            summary = item.get("summary", "")
            if not isinstance(summary, str):
                summary = ""

            recurrence = item.get("recurrence")
            if recurrence is not None and not isinstance(recurrence, list):
                recurrence = None

            attendees = self._parse_attendees(item.get("attendees"))
            organizer = self._parse_organizer(item.get("organizer"))

            return CalendarEvent(
                id=event_id,
                summary=summary,
                recurrence=recurrence,
                start=start,
                end=end,
                attendees=attendees,
                organizer=organizer,
            )
        except (KeyError, ValueError):
            return None

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse datetime string from Google Calendar API.

        Args:
            date_str: Date or datetime string.

        Returns:
            Parsed datetime object.
        """
        if "T" not in date_str:
            return datetime.fromisoformat(date_str)
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    def _parse_attendees(self, attendees_data: object) -> list[CalendarAttendee] | None:
        """Parse attendees from API response.

        Args:
            attendees_data: Raw attendees data from API.

        Returns:
            List of CalendarAttendee or None.
        """
        if not isinstance(attendees_data, list):
            return None

        result: list[CalendarAttendee] = []
        for attendee in attendees_data:
            if not isinstance(attendee, dict):
                continue

            email = attendee.get("email")
            if not isinstance(email, str):
                continue

            display_name = attendee.get("displayName")
            response_status = attendee.get("responseStatus")
            is_organizer = attendee.get("organizer", False)

            result.append(
                CalendarAttendee(
                    email=email,
                    display_name=display_name if isinstance(display_name, str) else None,
                    response_status=response_status if isinstance(response_status, str) else None,
                    is_organizer=bool(is_organizer),
                )
            )

        return result if result else None

    def _parse_organizer(self, organizer_data: object) -> CalendarOrganizer | None:
        """Parse organizer from API response.

        Args:
            organizer_data: Raw organizer data from API.

        Returns:
            CalendarOrganizer or None.
        """
        if not isinstance(organizer_data, dict):
            return None

        email = organizer_data.get("email")
        if not isinstance(email, str):
            return None

        display_name = organizer_data.get("displayName")
        is_self = organizer_data.get("self", False)

        return CalendarOrganizer(
            email=email,
            display_name=display_name if isinstance(display_name, str) else None,
            is_self=bool(is_self),
        )
