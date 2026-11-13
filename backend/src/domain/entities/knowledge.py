from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Knowledge:
    """Only explicitly imported meeting content enters shared storage."""

    id: UUID
    series_id: UUID
    occurrence_id: UUID
    source: Literal["upload", "meet_transcript"]
    google_doc_id: str | None
    title: str | None
    original_text: str
    normalized_text: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeDraft:
    """Selected content before the database assigns identity and creation time."""

    source: Literal["upload", "meet_transcript"]
    google_doc_id: str | None
    title: str | None
    original_text: str
    normalized_text: str
