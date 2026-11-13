from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.use_cases.agenda_use_cases import AgendaSources
from src.domain.entities.agenda import AgendaTopic
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import OccurrenceSummary


class TopicRequest(BaseModel):
    """A member's own proposed topic."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=2000)


class TopicView(BaseModel):
    """Public topic labels and caller ownership."""

    id: UUID
    title: str
    details: str | None
    author_label: str
    is_mine: bool
    created_at: datetime

    @classmethod
    def of(cls, topic: AgendaTopic, user_id: UUID) -> "TopicView":
        """Do not expose another participant's internal auth identifier."""
        return cls(
            id=topic.id,
            title=topic.title,
            details=topic.details,
            author_label=topic.author_label,
            is_mine=topic.submitted_by == user_id,
            created_at=topic.created_at,
        )


class AgendaView(BaseModel):
    """Public agenda with no internal aggregate metadata."""

    model_config = ConfigDict(from_attributes=True)
    occurrence_id: UUID
    content: str
    generated_at: datetime
    updated_at: datetime


class AgendaRequest(BaseModel):
    """A creator's saved agenda text."""

    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)


class KnowledgeSummary(BaseModel):
    """A shared document excerpt."""

    id: UUID
    source: Literal["upload", "meet_transcript"]
    title: str | None
    excerpt: str
    created_at: datetime

    @classmethod
    def of(cls, knowledge: Knowledge) -> "KnowledgeSummary":
        """Expose only the selected normalized content."""
        return cls(
            id=knowledge.id,
            source=knowledge.source,
            title=knowledge.title,
            excerpt=knowledge.normalized_text[:200],
            created_at=knowledge.created_at,
        )


class KnowledgeView(KnowledgeSummary):
    """The full selected document."""

    text: str


class UploadRequest(BaseModel):
    """Creator-selected plain meeting notes."""

    model_config = ConfigDict(extra="forbid")
    source: Literal["upload"]
    text: str = Field(min_length=1)


class DriveRequest(BaseModel):
    """A creator-picked live Drive candidate."""

    model_config = ConfigDict(extra="forbid")
    source: Literal["meet_transcript"]
    google_doc_id: str = Field(min_length=1)


AddKnowledgeRequest = Annotated[UploadRequest | DriveRequest, Field(discriminator="source")]


class AddKnowledgeResponse(BaseModel):
    """Persisted content with visible normalization diagnostics."""

    knowledge: KnowledgeSummary
    normalization_warning: str | None
    replacement_count: int


class OccurrenceDetail(BaseModel):
    """One meeting's complete member-visible content."""

    occurrence: OccurrenceSummary
    agenda: AgendaView | None
    topics: list[TopicView]
    knowledge: list[KnowledgeSummary]


class GenerateAgendaResponse(BaseModel):
    """Saved agenda and the exact source counts."""

    agenda: AgendaView
    sources: AgendaSources
