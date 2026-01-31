"""DictionaryEntry entity for domain layer.

Pure Python entity without external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DictionaryEntry:
    """Ubiquitous language dictionary entry entity.

    Attributes:
        id: Unique identifier for the entry.
        user_id: ID of the owning user.
        canonical_name: Official name (e.g., "Taro Kanazawa").
        description: Context description for LLM hint.
        created_at: Timestamp when the entry was created.
        updated_at: Timestamp when the entry was last updated.
    """

    id: UUID
    user_id: UUID
    canonical_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None
