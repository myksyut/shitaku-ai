"""Pydantic schemas for MeetingNote API.

Request/Response schemas for meeting note endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MeetingNoteCreate(BaseModel):
    """議事録作成リクエスト."""

    agent_id: UUID = Field(..., description="紐付けるエージェントのID")
    text: str = Field(..., min_length=1, description="議事録テキスト")
    meeting_date: datetime = Field(..., description="MTG開催日時")


class MeetingNoteResponse(BaseModel):
    """議事録レスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    original_text: str
    normalized_text: str
    meeting_date: datetime
    created_at: datetime
    is_normalized: bool  # 正規化が実行されたかどうか


class MeetingNoteUploadResponse(BaseModel):
    """議事録アップロードレスポンス（正規化結果含む）."""

    note: MeetingNoteResponse
    normalization_warning: str | None = None  # LLMエラー時の警告メッセージ
    replacement_count: int = 0  # 置換された箇所の数
