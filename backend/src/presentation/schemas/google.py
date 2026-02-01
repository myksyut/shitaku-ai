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
