"""トランスクリプトパーサー.

Google Meetトランスクリプトをパースし、構造化データに変換する。
AC12: テキスト取得・構造化
"""

import re

from src.domain.entities.meeting_transcript import (
    TranscriptEntry,
    TranscriptStructuredData,
)

# Google Meetトランスクリプトの形式: "話者名 (HH:MM)"
TRANSCRIPT_PATTERN = re.compile(r"^(?P<speaker>.+?)\s*\((?P<timestamp>\d{1,2}:\d{2})\)\s*$", re.MULTILINE)


def parse_transcript(raw_text: str) -> list[TranscriptEntry]:
    """Google Meetトランスクリプトをパースする.

    入力形式:
    ```
    宮木翔太 (10:02)
    じゃあ先週のタスクの進捗から確認しましょうか。

    金澤 (10:02)
    はい、RAGのチューニングは完了しました。
    ```

    Args:
        raw_text: 生のトランスクリプトテキスト

    Returns:
        TranscriptEntryのリスト
    """
    if not raw_text.strip():
        return []

    entries: list[TranscriptEntry] = []
    current_speaker: str | None = None
    current_timestamp: str | None = None
    current_text_lines: list[str] = []

    for line in raw_text.split("\n"):
        match = TRANSCRIPT_PATTERN.match(line)
        if match:
            # 前の発話を保存
            if current_speaker:
                text = "\n".join(current_text_lines).strip()
                if text:
                    entries.append(
                        TranscriptEntry(
                            speaker=current_speaker,
                            timestamp=current_timestamp or "",
                            text=text,
                        )
                    )
            # 新しい発話を開始
            current_speaker = match.group("speaker")
            current_timestamp = match.group("timestamp")
            current_text_lines = []
        elif line.strip():
            current_text_lines.append(line)

    # 最後の発話を保存
    if current_speaker:
        text = "\n".join(current_text_lines).strip()
        if text:
            entries.append(
                TranscriptEntry(
                    speaker=current_speaker,
                    timestamp=current_timestamp or "",
                    text=text,
                )
            )

    return entries


def parse_to_structured_data(raw_text: str) -> TranscriptStructuredData | None:
    """トランスクリプトを構造化データに変換する.

    Args:
        raw_text: 生のトランスクリプトテキスト

    Returns:
        TranscriptStructuredData、パースできない場合はNone
    """
    entries = parse_transcript(raw_text)
    if not entries:
        return None
    return TranscriptStructuredData(entries=entries)


def extract_speakers(raw_text: str) -> list[str]:
    """トランスクリプトから話者名を抽出する.

    Args:
        raw_text: 生のトランスクリプトテキスト

    Returns:
        ユニークな話者名のリスト
    """
    entries = parse_transcript(raw_text)
    return list({entry.speaker for entry in entries})
