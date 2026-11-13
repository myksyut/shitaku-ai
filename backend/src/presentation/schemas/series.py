from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClaimRequest(BaseModel):
    """An explicit event selection from an owned integration."""

    model_config = ConfigDict(extra="forbid")
    google_integration_id: UUID
    calendar_event_id: str = Field(min_length=1)


class SlackSelection(BaseModel):
    """Selected source IDs; names are resolved server-side."""

    model_config = ConfigDict(extra="forbid")
    integration_id: UUID
    channel_ids: list[str]


class SeriesSettingsRequest(BaseModel):
    """Only creator-owned settings, with no calendar identity columns."""

    model_config = ConfigDict(extra="forbid")
    description: str | None = Field(max_length=500)
    minutes_count: int = Field(ge=0, le=10)
    slack_message_days: int = Field(ge=1, le=30)
    slack: SlackSelection | None
