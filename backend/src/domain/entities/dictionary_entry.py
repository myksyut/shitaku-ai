from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, TypedDict
from uuid import UUID

DictionaryCategory = Literal["person", "project", "term", "customer", "abbreviation"]


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """One series' shared vocabulary."""

    id: UUID
    series_id: UUID
    canonical_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None = None
    category: DictionaryCategory | None = None
    aliases: list[str] = field(default_factory=list)


class DictionaryChanges(TypedDict, total=False):
    """Only editable vocabulary fields, with explicit null semantics."""

    canonical_name: str
    category: DictionaryCategory | None
    aliases: list[str]
    description: str | None
