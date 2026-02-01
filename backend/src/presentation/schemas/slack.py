"""Pydantic schemas for Slack API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SlackOAuthStartResponse(BaseModel):
    """OAuth開始レスポンス."""

    authorize_url: str


class SlackIntegrationResponse(BaseModel):
    """Slack連携レスポンス."""

    id: UUID
    workspace_id: str
    workspace_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SlackChannelResponse(BaseModel):
    """Slackチャンネルレスポンス."""

    id: str
    name: str


class SlackMessageResponse(BaseModel):
    """Slackメッセージレスポンス."""

    user_name: str
    text: str
    posted_at: str
