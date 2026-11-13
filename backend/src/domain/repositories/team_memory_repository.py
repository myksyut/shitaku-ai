from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.series import CreatorAccess, MemberAccess
from src.domain.entities.team_memory import ExtractedMemory, ExtractionApplyResult, MemoryItem, NewMemory, Resolution


class TeamMemoryRepository(ABC):
    """Series-scoped memory and atomic lifecycle operations."""

    @abstractmethod
    def list_items(self, series_id: UUID) -> list[MemoryItem]:
        """Read memory with original occurrence times."""

    @abstractmethod
    def get(self, series_id: UUID, item_id: UUID) -> MemoryItem | None:
        """Read an item inside its aggregate."""

    @abstractmethod
    def add(self, access: CreatorAccess, draft: NewMemory) -> None:
        """Add human-authored memory."""

    @abstractmethod
    def edit(self, access: CreatorAccess, item_id: UUID, draft: NewMemory) -> None:
        """Protect edited memory from future extraction."""

    @abstractmethod
    def set_resolution(self, access: MemberAccess, item_id: UUID, resolution: Resolution | None) -> None:
        """Set or clear an item's resolution."""

    @abstractmethod
    def delete(self, access: CreatorAccess, item_id: UUID) -> None:
        """Remove one aggregate-scoped item."""

    @abstractmethod
    def apply_extraction(
        self, access: CreatorAccess, occurrence_id: UUID, extracted: ExtractedMemory, input_at: datetime
    ) -> ExtractionApplyResult:
        """Apply idempotent extraction in one transaction."""
