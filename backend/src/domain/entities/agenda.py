from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AgendaTopic:
    """A member-authored suggestion owned by its author."""

    id: UUID
    series_id: UUID
    occurrence_id: UUID
    submitted_by: UUID
    author_label: str
    title: str
    details: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Agenda:
    """One persisted agenda per mirrored occurrence."""

    occurrence_id: UUID
    series_id: UUID
    content: str
    generated_at: datetime
    updated_at: datetime
