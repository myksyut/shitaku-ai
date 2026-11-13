from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from src.domain.entities.dictionary_entry import DictionaryCategory, DictionaryChanges


class DictionaryEntryCreate(BaseModel):
    """The creator's shared vocabulary input."""

    model_config = ConfigDict(extra="forbid")
    canonical_name: str = Field(min_length=1, max_length=100)
    category: DictionaryCategory | None
    aliases: list[str]
    description: str | None = Field(max_length=500)


class DictionaryEntryUpdate(BaseModel):
    """Partial vocabulary changes with explicit-null support."""

    model_config = ConfigDict(extra="forbid")
    canonical_name: str | None = Field(default=None, min_length=1, max_length=100)
    category: DictionaryCategory | None = None
    aliases: list[str] | None = None
    description: str | None = Field(default=None, max_length=500)

    @field_validator("canonical_name", "aliases")
    @classmethod
    def nonnullable_fields(cls, value: object) -> object:
        """Reject explicit nulls for fields that are only optional by omission."""
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    def changes(self) -> DictionaryChanges:
        """Return only the fields the request supplied."""
        return TypeAdapter[DictionaryChanges](DictionaryChanges).validate_python(self.model_dump(exclude_unset=True))


class DictionaryEntryView(BaseModel):
    """A series vocabulary entry."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    canonical_name: str
    category: DictionaryCategory | None
    aliases: list[str]
    description: str | None
