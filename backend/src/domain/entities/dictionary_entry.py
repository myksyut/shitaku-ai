"""DictionaryEntry entity for domain layer.

Pure Python entity without external dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

DictionaryCategory = Literal["person", "project", "term", "customer", "abbreviation"]


@dataclass
class DictionaryEntry:
    """Ubiquitous language dictionary entry entity.

    Attributes:
        id: Unique identifier for the entry.
        user_id: ID of the owning user.
        canonical_name: Official name (e.g., "Taro Kanazawa").
        description: Context description for LLM hint.
        agent_id: ID of the associated agent (optional).
        category: Category of the entry (person, project, term, customer, abbreviation).
        aliases: List of alternative names/spellings.
        created_at: Timestamp when the entry was created.
        updated_at: Timestamp when the entry was last updated.
    """

    id: UUID
    user_id: UUID
    canonical_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None = None
    agent_id: UUID | None = None
    category: DictionaryCategory | None = None
    aliases: list[str] = field(default_factory=list)
