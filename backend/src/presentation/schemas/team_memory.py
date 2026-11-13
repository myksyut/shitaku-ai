from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from src.domain.entities.series import parse_email
from src.domain.entities.team_memory import MemoryItem, NewMemory, Resolution


class NewDecisionRequest(BaseModel):
    """A creator's decision input."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["decision"]
    body: str = Field(min_length=1, max_length=1000)
    origin_occurrence_id: UUID


class NewActionRequest(BaseModel):
    """An action with an optional attendee assignee."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["action_item"]
    body: str = Field(min_length=1, max_length=1000)
    origin_occurrence_id: UUID
    assignee_email: str | None
    due_on: date | None

    @field_validator("assignee_email")
    @classmethod
    def normalize_assignee(cls, value: str | None) -> str | None:
        """Normalize and validate the assignee email."""
        if value is None:
            return None
        parsed = parse_email(value)
        if parsed is None:
            raise ValueError("Invalid assignee email")
        return parsed


class NewIssueRequest(BaseModel):
    """A creator's unresolved issue input."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["open_issue"]
    body: str = Field(min_length=1, max_length=1000)
    origin_occurrence_id: UUID


NewMemoryRequest = Annotated[NewDecisionRequest | NewActionRequest | NewIssueRequest, Field(discriminator="kind")]


def memory_draft(request: NewMemoryRequest) -> NewMemory:
    """Construct the domain union from a validated wire variant."""
    return TypeAdapter(NewMemory).validate_python(request.model_dump())


class ResolutionRequest(BaseModel):
    """A resolution, or null to reopen."""

    model_config = ConfigDict(extra="forbid")
    resolution: Resolution | None


class MemoryView(BaseModel):
    """Fields common to every memory item view."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    body: str
    origin_occurrence_id: UUID
    origin_start_at: datetime
    extracted: bool
    closed_at: datetime | None


class DecisionView(MemoryView):
    """Decision wire variant."""

    kind: Literal["decision"]
    resolution: Literal["reversed"] | None


class ActionView(MemoryView):
    """Action wire variant."""

    kind: Literal["action_item"]
    assignee_email: str | None
    due_on: date | None
    resolution: Literal["done", "dropped"] | None
    carry_over: int


class IssueView(MemoryView):
    """Issue wire variant."""

    kind: Literal["open_issue"]
    resolution: Literal["resolved", "dropped"] | None
    carry_over: int


PublicMemory = Annotated[DecisionView | ActionView | IssueView, Field(discriminator="kind")]


class TeamMemoryResponse(BaseModel):
    """The entire refreshed team memory board."""

    items: list[PublicMemory]


def memory_response(items: list[MemoryItem]) -> TeamMemoryResponse:
    """Project memory items into the public response."""
    return TeamMemoryResponse(items=TypeAdapter(list[PublicMemory]).validate_python(items, from_attributes=True))


class ExtractionReport(TeamMemoryResponse):
    """Extraction persistence counts and input truncation signal."""

    created: int
    closed: int
    truncated: bool
