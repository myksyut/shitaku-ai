from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from src.domain.entities.series import Attendee, CalendarSnapshot, OccurrenceSlot, parse_email

CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"


class CalendarPerson(BaseModel):
    """Untrusted Google person fields."""

    email: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    resource: bool = False


class CalendarTime(BaseModel):
    """Google timed and all-day event timestamps."""

    date_time: datetime | None = Field(default=None, alias="dateTime")
    date: str | None = None

    def instant(self) -> datetime | None:
        """Represent all-day slots at UTC midnight."""
        return self.date_time or (datetime.fromisoformat(self.date).replace(tzinfo=UTC) if self.date else None)


class CalendarEvent(BaseModel):
    """Boundary schema for masters and instances."""

    id: str
    ical_uid: str = Field(default="", alias="iCalUID")
    summary: str = "(無題)"
    recurrence: list[str] = Field(default_factory=list)
    organizer: CalendarPerson | None = None
    attendees: list[CalendarPerson] = Field(default_factory=list)
    attendees_omitted: bool = Field(default=False, alias="attendeesOmitted")
    start: CalendarTime = Field(default_factory=CalendarTime)
    original_start_time: CalendarTime = Field(default_factory=CalendarTime, alias="originalStartTime")
    status: str = "confirmed"


class CalendarPage(BaseModel):
    """A paginated Calendar response."""

    items: list[CalendarEvent] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


def parse_snapshot(
    master: CalendarEvent, instances: list[CalendarEvent], window_start: datetime, window_end: datetime
) -> CalendarSnapshot:
    """Drop rooms, normalize people, and retain stable instance identities."""
    attendees: dict[str, Attendee] = {}
    people = [(p, False) for p in master.attendees]
    if master.organizer:
        people.append((master.organizer, True))
    for person, organizer in people:
        email = parse_email(person.email)
        if email and not person.resource and not email.endswith("@resource.calendar.google.com"):
            attendees[email] = Attendee(email, person.display_name, organizer)
    slots: list[OccurrenceSlot] = []
    for instance in instances:
        original = instance.original_start_time.instant()
        start = instance.start.instant() or original
        if original is not None and start is not None:
            slots.append(OccurrenceSlot(original, start, instance.status == "cancelled"))
    return CalendarSnapshot(
        master.ical_uid,
        master.id,
        master.summary,
        next((r for r in master.recurrence if r.startswith("RRULE:")), None),
        tuple(attendees.values()),
        master.attendees_omitted,
        tuple(slots),
        window_start,
        window_end,
    )


class GoogleCalendarClient:
    """Read calendar snapshots without storing unselected events."""

    def __init__(self, access_token: str) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}"}

    def _pages(self, path: str, params: dict[str, str]) -> list[CalendarEvent]:
        result: list[CalendarEvent] = []
        with httpx.Client(timeout=30) as client:
            while True:
                response = client.get(f"{CALENDAR_API_URL}/{path}", headers=self._headers, params=params)
                response.raise_for_status()
                page = CalendarPage.model_validate(response.json())
                result.extend(page.items)
                if not page.next_page_token:
                    return result
                params = {**params, "pageToken": page.next_page_token}

    def list_recurring_masters(self) -> list[CalendarSnapshot]:
        """Offer live recurring masters from the selected primary calendar."""
        now = datetime.now(UTC)
        window_end = now + timedelta(days=365)
        events = self._pages(
            "calendars/primary/events",
            {
                "singleEvents": "false",
                "maxResults": "2500",
                "timeMin": now.isoformat(),
                "timeMax": window_end.isoformat(),
            },
        )
        return [
            parse_snapshot(e, [], now, window_end)
            for e in events
            if e.recurrence and e.ical_uid and e.status != "cancelled"
        ]

    def snapshot(self, event_id: str, now: datetime) -> CalendarSnapshot | None:
        """Fetch a recurring master and its instances in the 35-day mirror window."""
        path = f"calendars/primary/events/{quote(event_id, safe='')}"
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{CALENDAR_API_URL}/{path}", headers=self._headers)
        if response.status_code in (404, 410):
            return None
        response.raise_for_status()
        master = CalendarEvent.model_validate(response.json())
        if master.status == "cancelled":
            return None
        if not master.recurrence or not master.ical_uid:
            raise ValueError("Event is not recurring")
        window_start, window_end = now - timedelta(days=35), now + timedelta(days=35)
        instances = self._pages(
            f"{path}/instances",
            {
                "timeMin": window_start.isoformat(),
                "timeMax": window_end.isoformat(),
                "showDeleted": "true",
                "maxResults": "2500",
            },
        )
        return parse_snapshot(master, instances, window_start, window_end)
