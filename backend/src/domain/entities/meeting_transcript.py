"""トランスクリプトエンティティ."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class TranscriptEntry:
    """トランスクリプトの1エントリ.

    Attributes:
        speaker: 話者名
        timestamp: タイムスタンプ（HH:MM形式）
        text: 発話内容
    """

    speaker: str
    timestamp: str
    text: str


@dataclass
class TranscriptStructuredData:
    """構造化トランスクリプトデータ.

    Attributes:
        entries: トランスクリプトエントリのリスト
    """

    entries: list[TranscriptEntry]

    def get_speakers(self) -> list[str]:
        """全話者名を取得する.

        Returns:
            ユニークな話者名のリスト
        """
        return list({entry.speaker for entry in self.entries})


@dataclass
class MeetingTranscript:
    """会議トランスクリプトエンティティ.

    Attributes:
        id: トランスクリプトID
        recurring_meeting_id: 紐付けられた定例MTG ID
        meeting_date: 会議日時
        google_doc_id: Google DocsのドキュメントID
        raw_text: 生テキスト
        structured_data: 構造化データ（パース済み）
        match_confidence: 紐付け信頼度（0.0-1.0）
        created_at: 作成日時
    """

    id: UUID
    recurring_meeting_id: UUID
    meeting_date: datetime
    google_doc_id: str
    raw_text: str
    structured_data: TranscriptStructuredData | None
    match_confidence: float
    created_at: datetime

    def is_auto_linked(self) -> bool:
        """自動紐付けされたかを判定する.

        信頼度が0.7以上の場合は自動紐付け。

        Returns:
            自動紐付けの場合True
        """
        return self.match_confidence >= 0.7

    def needs_manual_confirmation(self) -> bool:
        """手動確認が必要かを判定する.

        信頼度が0.7未満の場合は手動確認が必要。

        Returns:
            手動確認が必要な場合True
        """
        return self.match_confidence < 0.7
