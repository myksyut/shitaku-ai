from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

Resolution = Literal["reversed", "done", "dropped", "resolved"]
MemoryKind = Literal["decision", "action_item", "open_issue"]
RESOLUTIONS_BY_KIND: dict[MemoryKind, frozenset[str]] = {
    "decision": frozenset({"reversed"}),
    "action_item": frozenset({"done", "dropped"}),
    "open_issue": frozenset({"resolved", "dropped"}),
}


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryBase:
    """Shared provenance, separate from kind-specific invariants."""

    id: UUID
    series_id: UUID
    body: str
    origin_occurrence_id: UUID
    origin_start_at: datetime
    extracted: bool
    human_updated_at: datetime | None = None
    extraction_key: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Decision(MemoryBase):
    """An active or explicitly reversed decision."""

    kind: Literal["decision"] = "decision"
    resolution: Literal["reversed"] | None = None
    closed_at: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ActionItem(MemoryBase):
    """An assigned action with a kind-safe closure."""

    kind: Literal["action_item"] = "action_item"
    assignee_email: str | None = None
    due_on: date | None = None
    resolution: Literal["done", "dropped"] | None = None
    closed_at: datetime | None = None
    carry_over: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class OpenIssue(MemoryBase):
    """An unresolved discussion carried across meetings."""

    kind: Literal["open_issue"] = "open_issue"
    resolution: Literal["resolved", "dropped"] | None = None
    closed_at: datetime | None = None
    carry_over: int = 0


MemoryItem = Decision | ActionItem | OpenIssue


@dataclass(frozen=True, slots=True, kw_only=True)
class NewDecision:
    """A new decision tied to one occurrence."""

    body: str
    origin_occurrence_id: UUID
    kind: Literal["decision"] = "decision"


@dataclass(frozen=True, slots=True, kw_only=True)
class NewActionItem:
    """A new action with attendee-bound assignment."""

    body: str
    origin_occurrence_id: UUID
    assignee_email: str | None = None
    due_on: date | None = None
    kind: Literal["action_item"] = "action_item"


@dataclass(frozen=True, slots=True, kw_only=True)
class NewOpenIssue:
    """A new issue tied to one occurrence."""

    body: str
    origin_occurrence_id: UUID
    kind: Literal["open_issue"] = "open_issue"


NewMemory = NewDecision | NewActionItem | NewOpenIssue


@dataclass(frozen=True, slots=True)
class ClosureRequest:
    """A closure referring to a validated existing item."""

    item_id: UUID
    resolution: Resolution


@dataclass(frozen=True, slots=True)
class ExtractedMemory:
    """Validated tool-use output and its input-budget signal."""

    new_items: tuple[NewMemory, ...]
    closures: tuple[ClosureRequest, ...]
    truncated: bool
