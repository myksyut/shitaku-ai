"""Pydantic schemas for dictionary API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DictionaryEntryCreate(BaseModel):
    """Schema for creating a dictionary entry."""

    canonical_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class DictionaryEntryUpdate(BaseModel):
    """Schema for updating a dictionary entry."""

    canonical_name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class DictionaryEntryResponse(BaseModel):
    """Schema for dictionary entry response."""

    id: UUID
    canonical_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
