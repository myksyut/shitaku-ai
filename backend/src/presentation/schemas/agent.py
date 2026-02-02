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
    transcript_count: int = Field(default=3, ge=0, le=10, description="参照するトランスクリプト数（0-10）")
    slack_message_days: int = Field(default=7, ge=1, le=30, description="Slackメッセージの参照日数（1-30）")


class AgentUpdate(BaseModel):
    """エージェント更新リクエスト."""

    name: str | None = Field(None, min_length=1, max_length=100, description="エージェント名")
    description: str | None = Field(None, max_length=500, description="エージェントの説明")
    slack_channel_id: str | None = Field(None, description="SlackチャンネルID")
    transcript_count: int | None = Field(None, ge=0, le=10, description="参照するトランスクリプト数（0-10）")
    slack_message_days: int | None = Field(None, ge=1, le=30, description="Slackメッセージの参照日数（1-30）")


class AgentResponse(BaseModel):
    """エージェントレスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    slack_channel_id: str | None
    transcript_count: int
    slack_message_days: int
    created_at: datetime
    updated_at: datetime | None
