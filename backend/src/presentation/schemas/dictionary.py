"""Pydantic schemas for dictionary API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DictionaryCategoryEnum(str, Enum):
    """Enum for dictionary entry categories."""

    PERSON = "person"
    PROJECT = "project"
    TERM = "term"
    CUSTOMER = "customer"
    ABBREVIATION = "abbreviation"


class DictionaryEntryCreate(BaseModel):
    """Schema for creating a dictionary entry."""

    canonical_name: str = Field(..., min_length=1, max_length=100)
    category: DictionaryCategoryEnum
    aliases: list[str] = Field(default_factory=list)
    description: str | None = Field(None, max_length=500)


class DictionaryEntryUpdate(BaseModel):
    """Schema for updating a dictionary entry."""

    canonical_name: str | None = Field(None, min_length=1, max_length=100)
    category: DictionaryCategoryEnum | None = None
    aliases: list[str] | None = None
    description: str | None = Field(None, max_length=500)


class DictionaryEntryResponse(BaseModel):
    """Schema for dictionary entry response."""

    id: UUID
    agent_id: UUID | None = None
    canonical_name: str
    category: DictionaryCategoryEnum | None = None
    aliases: list[str] = Field(default_factory=list)
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
