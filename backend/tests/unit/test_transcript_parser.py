"""トランスクリプトパーサーのテスト.

AC12: テキスト取得・構造化
"""

from src.domain.services.transcript_parser import (
    TRANSCRIPT_PATTERN,
    extract_speakers,
    parse_to_structured_data,
    parse_transcript,
)


class TestTranscriptParser:
    """トランスクリプトパーサーのテスト."""

    def test_parse_simple_transcript(self) -> None:
        """シンプルなトランスクリプトがパースできる."""
        raw_text = """宮木翔太 (10:02)
じゃあ先週のタスクの進捗から確認しましょうか。

金澤 (10:02)
はい、RAGのチューニングは完了しました。"""

        entries = parse_transcript(raw_text)

        assert len(entries) == 2
        assert entries[0].speaker == "宮木翔太"
        assert entries[0].timestamp == "10:02"
        assert "先週のタスク" in entries[0].text
        assert entries[1].speaker == "金澤"
        assert "RAGのチューニング" in entries[1].text

    def test_parse_multiline_utterance(self) -> None:
        """複数行の発話がパースできる."""
        raw_text = """田中 (14:30)
これは1行目です。
これは2行目です。
これは3行目です。

鈴木 (14:32)
了解です。"""

        entries = parse_transcript(raw_text)

        assert len(entries) == 2
        assert entries[0].speaker == "田中"
        assert "1行目" in entries[0].text
        assert "2行目" in entries[0].text
        assert "3行目" in entries[0].text

    def test_parse_empty_text(self) -> None:
        """空テキストは空リストを返す."""
        entries = parse_transcript("")
        assert entries == []

    def test_parse_no_match(self) -> None:
        """パターンにマッチしないテキストは空リストを返す."""
        raw_text = "This is not a transcript format."
        entries = parse_transcript(raw_text)
        assert entries == []

    def test_parse_single_digit_timestamp(self) -> None:
        """1桁の時間もパースできる."""
        raw_text = """山田 (9:05)
おはようございます。"""

        entries = parse_transcript(raw_text)

        assert len(entries) == 1
        assert entries[0].speaker == "山田"
        assert entries[0].timestamp == "9:05"

    def test_transcript_pattern_matches_expected_format(self) -> None:
        """正規表現パターンが期待通りにマッチする."""
        test_cases = [
            ("宮木翔太 (10:02)", True),
            ("金澤 (10:02)", True),
            ("User Name (9:05)", True),
            ("Invalid Format", False),
            ("(10:02) Name", False),
        ]

        for text, should_match in test_cases:
            match = TRANSCRIPT_PATTERN.match(text)
            assert (match is not None) == should_match, f"Failed for: {text}"


class TestParseToStructuredData:
    """parse_to_structured_data関数のテスト."""

    def test_returns_structured_data_for_valid_transcript(self) -> None:
        """有効なトランスクリプトでTranscriptStructuredDataを返す."""
        raw_text = """田中 (10:00)
会議を始めましょう。"""

        result = parse_to_structured_data(raw_text)

        assert result is not None
        assert len(result.entries) == 1
        assert result.entries[0].speaker == "田中"

    def test_returns_none_for_empty_transcript(self) -> None:
        """空テキストでNoneを返す."""
        result = parse_to_structured_data("")
        assert result is None

    def test_returns_none_for_invalid_format(self) -> None:
        """無効なフォーマットでNoneを返す."""
        result = parse_to_structured_data("invalid text without pattern")
        assert result is None


class TestExtractSpeakers:
    """extract_speakers関数のテスト."""

    def test_extracts_unique_speakers(self) -> None:
        """ユニークな話者名を抽出する."""
        raw_text = """田中 (10:00)
発言1

鈴木 (10:01)
発言2

田中 (10:02)
発言3"""

        speakers = extract_speakers(raw_text)

        assert len(speakers) == 2
        assert "田中" in speakers
        assert "鈴木" in speakers

    def test_returns_empty_for_no_speakers(self) -> None:
        """話者がいない場合は空リストを返す."""
        speakers = extract_speakers("")
        assert speakers == []
