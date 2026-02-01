"""Pydantic schemas for Agenda API.

Request/Response schemas for agenda endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgendaGenerateRequest(BaseModel):
    """アジェンダ生成リクエスト."""

    agent_id: UUID = Field(..., description="アジェンダを生成するエージェントのID")


class AgendaUpdate(BaseModel):
    """アジェンダ更新リクエスト."""

    content: str = Field(..., min_length=1, description="アジェンダ内容")


class AgendaResponse(BaseModel):
    """アジェンダレスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    content: str
    source_note_id: UUID | None
    generated_at: datetime
    created_at: datetime
    updated_at: datetime | None


class DataSourcesInfo(BaseModel):
    """使用されたデータソース情報."""

    has_meeting_note: bool
    has_slack_messages: bool
    slack_message_count: int
    dictionary_entry_count: int
    slack_error: str | None = None


class AgendaGenerateResponse(BaseModel):
    """アジェンダ生成レスポンス."""

    agenda: AgendaResponse
    data_sources: DataSourcesInfo
