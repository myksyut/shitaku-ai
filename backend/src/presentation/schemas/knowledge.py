"""Pydantic schemas for Knowledge API.

Request/Response schemas for knowledge endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeCreate(BaseModel):
    """ナレッジ作成リクエスト."""

    agent_id: UUID = Field(..., description="紐付けるエージェントのID")
    text: str = Field(..., min_length=1, description="ナレッジテキスト")


class KnowledgeResponse(BaseModel):
    """ナレッジレスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    original_text: str
    normalized_text: str
    meeting_date: datetime
    created_at: datetime
    is_normalized: bool  # 正規化が実行されたかどうか


class KnowledgeUploadResponse(BaseModel):
    """ナレッジアップロードレスポンス（正規化結果含む）."""

    knowledge: KnowledgeResponse
    normalization_warning: str | None = None  # LLMエラー時の警告メッセージ
    replacement_count: int = 0  # 置換された箇所の数
