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


class RecurringMeetingResponse(BaseModel):
    """定例MTGレスポンス."""

    id: UUID
    google_event_id: str
    title: str
    frequency: str
    attendees: list[str]
    next_occurrence: datetime
    agent_id: UUID | None

    model_config = {"from_attributes": True}


class RecurringMeetingsResponse(BaseModel):
    """定例MTG一覧レスポンス."""

    meetings: list[RecurringMeetingResponse]


class SyncResultResponse(BaseModel):
    """同期結果レスポンス."""

    created: int
    updated: int


class LinkAgentRequest(BaseModel):
    """エージェント紐付けリクエスト."""

    agent_id: UUID
