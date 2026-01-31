"""Pydantic schemas for Agent API.

Request/Response schemas for agent endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    """エージェント作成リクエスト."""

    name: str = Field(..., min_length=1, max_length=100, description="エージェント名")
    description: str | None = Field(None, max_length=500, description="エージェントの説明")
    slack_channel_id: str | None = Field(None, description="SlackチャンネルID")


class AgentUpdate(BaseModel):
    """エージェント更新リクエスト."""

    name: str | None = Field(None, min_length=1, max_length=100, description="エージェント名")
    description: str | None = Field(None, max_length=500, description="エージェントの説明")
    slack_channel_id: str | None = Field(None, description="SlackチャンネルID")


class AgentResponse(BaseModel):
    """エージェントレスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    slack_channel_id: str | None
    created_at: datetime
    updated_at: datetime | None
