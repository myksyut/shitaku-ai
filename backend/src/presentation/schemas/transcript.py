"""Pydantic schemas for Transcript API.

Request/Response schemas for transcript endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptEntrySchema(BaseModel):
    """トランスクリプトエントリスキーマ."""

    speaker: str = Field(..., description="話者名")
    timestamp: str = Field(..., description="タイムスタンプ（HH:MM形式）")
    text: str = Field(..., description="発話内容")


class TranscriptStructuredDataSchema(BaseModel):
    """構造化トランスクリプトデータスキーマ."""

    entries: list[TranscriptEntrySchema] = Field(default_factory=list, description="エントリのリスト")


class TranscriptCreate(BaseModel):
    """トランスクリプト作成リクエスト."""

    recurring_meeting_id: UUID = Field(..., description="定例MTG ID")
    meeting_date: datetime = Field(..., description="会議日時")
    google_doc_id: str = Field(..., min_length=1, description="Google DocsのドキュメントID")
    raw_text: str = Field(..., description="生テキスト")
    structured_data: TranscriptStructuredDataSchema | None = Field(None, description="構造化データ")
    match_confidence: float = Field(..., ge=0.0, le=1.0, description="紐付け信頼度（0.0-1.0）")


class TranscriptResponse(BaseModel):
    """トランスクリプトレスポンス."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recurring_meeting_id: UUID
    meeting_date: datetime
    google_doc_id: str
    raw_text: str
    structured_data: TranscriptStructuredDataSchema | None
    match_confidence: float
    is_auto_linked: bool = Field(..., description="自動紐付けされたか（信頼度0.7以上）")
    needs_manual_confirmation: bool = Field(..., description="手動確認が必要か（信頼度0.7未満）")
    created_at: datetime


class LinkTranscriptRequest(BaseModel):
    """トランスクリプト手動紐付けリクエスト."""

    recurring_meeting_id: UUID = Field(..., description="紐付け先の定例MTG ID")


class SyncResultResponse(BaseModel):
    """同期結果レスポンス."""

    synced_count: int = Field(..., description="同期成功件数")
    skipped_count: int = Field(..., description="スキップ件数（重複）")
    error_count: int = Field(..., description="エラー件数")
    synced_transcripts: list[TranscriptResponse] = Field(
        default_factory=list, description="同期されたトランスクリプト一覧"
    )
