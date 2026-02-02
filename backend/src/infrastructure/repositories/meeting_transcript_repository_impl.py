"""MeetingTranscriptRepository implementation using Supabase.

Infrastructure layer implementation of MeetingTranscriptRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from supabase import Client

from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptEntry,
    TranscriptStructuredData,
)
from src.domain.repositories.meeting_transcript_repository import (
    MeetingTranscriptRepository,
)


class MeetingTranscriptRepositoryImpl(MeetingTranscriptRepository):
    """会議トランスクリプトリポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス
        """
        self.client = client

    async def create(self, transcript: MeetingTranscript) -> MeetingTranscript:
        """トランスクリプトを作成する."""
        data: dict[str, Any] = {
            "id": str(transcript.id),
            "recurring_meeting_id": str(transcript.recurring_meeting_id),
            "meeting_date": transcript.meeting_date.isoformat(),
            "google_doc_id": transcript.google_doc_id,
            "raw_text": transcript.raw_text,
            "structured_data": self._serialize_structured_data(transcript.structured_data),
            "match_confidence": transcript.match_confidence,
            "created_at": transcript.created_at.isoformat(),
        }
        self.client.table("meeting_transcripts").insert(data).execute()
        return transcript

    async def get_by_id(self, transcript_id: UUID) -> MeetingTranscript | None:
        """IDでトランスクリプトを取得する."""
        result = (
            self.client.table("meeting_transcripts").select("*").eq("id", str(transcript_id)).maybe_single().execute()
        )

        if result is None or not result.data:
            return None

        return self._to_entity(cast(dict[str, Any], result.data))

    async def get_by_recurring_meeting(
        self,
        recurring_meeting_id: UUID,
        limit: int | None = None,
    ) -> list[MeetingTranscript]:
        """定例MTGのトランスクリプト一覧を取得する."""
        query = (
            self.client.table("meeting_transcripts")
            .select("*")
            .eq("recurring_meeting_id", str(recurring_meeting_id))
            .order("meeting_date", desc=True)
        )

        if limit is not None:
            query = query.limit(limit)

        result = query.execute()
        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    async def get_by_date_range(
        self,
        recurring_meeting_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[MeetingTranscript]:
        """指定期間内のトランスクリプトを取得する."""
        result = (
            self.client.table("meeting_transcripts")
            .select("*")
            .eq("recurring_meeting_id", str(recurring_meeting_id))
            .gte("meeting_date", start_date.isoformat())
            .lte("meeting_date", end_date.isoformat())
            .order("meeting_date", desc=False)
            .execute()
        )
        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    async def get_by_google_doc_id(
        self,
        google_doc_id: str,
        user_id: UUID,
    ) -> MeetingTranscript | None:
        """Google Doc IDでトランスクリプトを取得する.

        RLS経由でuser_idフィルタリングが適用されるが、
        明示的にrecurring_meetingsテーブルをJOINしてuser_idを検証する。
        """
        # recurring_meetingsを経由してuser_idでフィルタリング
        result = (
            self.client.table("meeting_transcripts")
            .select("*, recurring_meetings!inner(user_id)")
            .eq("google_doc_id", google_doc_id)
            .eq("recurring_meetings.user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        return self._to_entity(cast(dict[str, Any], result.data))

    async def update(self, transcript: MeetingTranscript) -> MeetingTranscript:
        """トランスクリプトを更新する."""
        data: dict[str, Any] = {
            "recurring_meeting_id": str(transcript.recurring_meeting_id),
            "meeting_date": transcript.meeting_date.isoformat(),
            "raw_text": transcript.raw_text,
            "structured_data": self._serialize_structured_data(transcript.structured_data),
            "match_confidence": transcript.match_confidence,
        }
        self.client.table("meeting_transcripts").update(data).eq("id", str(transcript.id)).execute()
        return transcript

    async def get_needing_confirmation(
        self,
        user_id: UUID,
    ) -> list[MeetingTranscript]:
        """手動確認が必要なトランスクリプト一覧を取得する.

        match_confidenceが0.7未満のトランスクリプトを取得。
        """
        result = (
            self.client.table("meeting_transcripts")
            .select("*, recurring_meetings!inner(user_id)")
            .eq("recurring_meetings.user_id", str(user_id))
            .lt("match_confidence", 0.7)
            .order("meeting_date", desc=True)
            .execute()
        )
        return [self._to_entity(cast(dict[str, Any], row)) for row in result.data]

    async def delete(self, transcript_id: UUID) -> bool:
        """トランスクリプトを削除する."""
        result = self.client.table("meeting_transcripts").delete().eq("id", str(transcript_id)).execute()
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> MeetingTranscript:
        """DB結果をエンティティに変換する."""
        created_at_str = data["created_at"]
        meeting_date_str = data["meeting_date"]

        # Handle timezone-aware ISO format
        created_at = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
        meeting_date = datetime.fromisoformat(str(meeting_date_str).replace("Z", "+00:00"))

        # Parse structured_data from JSONB
        structured_data = self._deserialize_structured_data(data.get("structured_data"))

        return MeetingTranscript(
            id=UUID(str(data["id"])),
            recurring_meeting_id=UUID(str(data["recurring_meeting_id"])),
            meeting_date=meeting_date,
            google_doc_id=str(data["google_doc_id"]),
            raw_text=str(data["raw_text"]),
            structured_data=structured_data,
            match_confidence=float(data["match_confidence"]),
            created_at=created_at,
        )

    def _serialize_structured_data(self, structured_data: TranscriptStructuredData | None) -> dict[str, Any] | None:
        """TranscriptStructuredDataをJSONB用の辞書に変換する."""
        if structured_data is None:
            return None

        return {
            "entries": [
                {
                    "speaker": entry.speaker,
                    "timestamp": entry.timestamp,
                    "text": entry.text,
                }
                for entry in structured_data.entries
            ]
        }

    def _deserialize_structured_data(self, data: dict[str, Any] | None) -> TranscriptStructuredData | None:
        """JSONB辞書をTranscriptStructuredDataに変換する."""
        if data is None:
            return None

        entries_data = data.get("entries", [])
        entries = [
            TranscriptEntry(
                speaker=str(entry.get("speaker", "")),
                timestamp=str(entry.get("timestamp", "")),
                text=str(entry.get("text", "")),
            )
            for entry in entries_data
        ]

        return TranscriptStructuredData(entries=entries)
