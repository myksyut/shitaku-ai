"""Pydantic schemas for Google API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GoogleOAuthStartResponse(BaseModel):
    """OAuth開始レスポンス."""

    authorize_url: str


class GoogleIntegrationResponse(BaseModel):
    """Google連携レスポンス."""

    id: UUID
    email: str
    granted_scopes: list[str]
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AdditionalScopesRequest(BaseModel):
    """追加スコープリクエスト."""

    scopes: list[str] | None = None


class AttendeeResponse(BaseModel):
    """参加者レスポンス."""

    email: str
    name: str | None


class RecurringMeetingResponse(BaseModel):
    """定例MTGレスポンス."""

    id: UUID
    google_event_id: str
    title: str
    rrule: str
    frequency: str
    attendees: list[AttendeeResponse]
    next_occurrence: datetime
    agent_id: UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class LinkRecurringMeetingRequest(BaseModel):
    """定例MTG紐付けリクエスト."""

    recurring_meeting_id: UUID


class LinkRecurringMeetingResponse(BaseModel):
    """定例MTG紐付けレスポンス."""

    message: str
    recurring_meeting: RecurringMeetingResponse


class UnlinkRecurringMeetingResponse(BaseModel):
    """定例MTG紐付け解除レスポンス."""

    message: str


class SyncProviderTokenRequest(BaseModel):
    """Supabase AuthのproviderTokenを同期するリクエスト."""

    provider_token: str
    provider_refresh_token: str | None = None
    email: str
    scopes: list[str] | None = None


class SyncProviderTokenResponse(BaseModel):
    """providerToken同期レスポンス."""

    success: bool
    message: str
    integration_id: UUID | None = None
