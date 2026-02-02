"""紐付けアルゴリズムのテスト.

AC13: ドキュメント名と会議名マッチング
AC14: 日時比較
AC15: 参加者名と話者名照合
"""

from datetime import datetime, timedelta

import pytest

from src.domain.services.matching_algorithm import (
    calculate_jaccard,
    calculate_match_confidence,
    calculate_string_similarity,
    calculate_time_score,
)


class TestStringMatching:
    """AC13: ドキュメント名と会議名マッチングのテスト."""

    def test_exact_match(self) -> None:
        """完全一致の場合は1.0."""
        assert calculate_string_similarity("Weekly Standup", "Weekly Standup") == 1.0

    def test_partial_match(self) -> None:
        """部分一致の場合は0より大きい."""
        similarity = calculate_string_similarity("Weekly Standup - 2026-02-01", "Weekly Standup")
        assert 0 < similarity < 1.0

    def test_no_match(self) -> None:
        """完全不一致の場合は0."""
        similarity = calculate_string_similarity("ABC", "XYZ")
        assert similarity == 0.0

    def test_empty_string(self) -> None:
        """空文字列の場合は0."""
        assert calculate_string_similarity("", "test") == 0.0
        assert calculate_string_similarity("test", "") == 0.0

    def test_case_insensitive(self) -> None:
        """大文字小文字を区別しない."""
        similarity = calculate_string_similarity("Weekly Standup", "weekly standup")
        assert similarity == 1.0


class TestTimeMatching:
    """AC14: 日時比較のテスト."""

    def test_exact_time_match(self) -> None:
        """同時刻の場合は1.0."""
        now = datetime.now()
        assert calculate_time_score(now, now) == 1.0

    def test_within_1_hour(self) -> None:
        """1時間以内の場合は0.95以上."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        score = calculate_time_score(now, one_hour_ago)
        assert score >= 0.95

    def test_within_24_hours(self) -> None:
        """24時間以内の場合は0より大きい."""
        now = datetime.now()
        one_day_ago = now - timedelta(hours=24)
        score = calculate_time_score(now, one_day_ago)
        assert 0 <= score <= 1.0

    def test_over_24_hours(self) -> None:
        """24時間超の場合は0."""
        now = datetime.now()
        two_days_ago = now - timedelta(hours=48)
        assert calculate_time_score(now, two_days_ago) == 0.0

    def test_12_hours_difference(self) -> None:
        """12時間差の場合は0.5."""
        now = datetime.now()
        half_day_ago = now - timedelta(hours=12)
        score = calculate_time_score(now, half_day_ago)
        assert score == pytest.approx(0.5, abs=0.01)


class TestAttendeeMatching:
    """AC15: 参加者名と話者名照合のテスト."""

    def test_full_match(self) -> None:
        """全員一致の場合は1.0."""
        attendees = {"user1", "user2", "user3"}
        speakers = {"user1", "user2", "user3"}
        assert calculate_jaccard(attendees, speakers) == 1.0

    def test_partial_match(self) -> None:
        """部分一致の場合は0より大きい."""
        attendees = {"user1", "user2", "user3"}
        speakers = {"user1", "user4"}
        score = calculate_jaccard(attendees, speakers)
        assert 0 < score < 1.0
        # Jaccard: |intersection| / |union| = 1 / 4 = 0.25
        assert score == pytest.approx(0.25)

    def test_no_match(self) -> None:
        """完全不一致の場合は0."""
        attendees = {"user1", "user2"}
        speakers = {"user3", "user4"}
        assert calculate_jaccard(attendees, speakers) == 0.0

    def test_empty_sets(self) -> None:
        """空集合の場合は0."""
        assert calculate_jaccard(set(), {"user1"}) == 0.0
        assert calculate_jaccard({"user1"}, set()) == 0.0
        assert calculate_jaccard(set(), set()) == 0.0


class TestMatchConfidence:
    """calculate_match_confidence統合テスト."""

    def test_high_confidence_match(self) -> None:
        """高信頼度（>=0.7）のケース."""
        now = datetime.now()
        confidence = calculate_match_confidence(
            doc_name="Weekly Standup - 2026-02-01",
            doc_created=now - timedelta(hours=1),
            event_summary="Weekly Standup",
            event_datetime=now - timedelta(hours=1),
            event_attendees=["user1@example.com", "user2@example.com"],
            transcript_speakers=["user1", "user2"],
        )
        assert confidence >= 0.7

    def test_low_confidence_match(self) -> None:
        """低信頼度（<0.7）のケース."""
        now = datetime.now()
        confidence = calculate_match_confidence(
            doc_name="Random Document",
            doc_created=now - timedelta(hours=30),  # 24時間超
            event_summary="Weekly Standup",
            event_datetime=now,
            event_attendees=["user1@example.com"],
            transcript_speakers=["UnknownUser"],
        )
        assert confidence < 0.7

    def test_perfect_match(self) -> None:
        """完全一致のケース."""
        now = datetime.now()
        confidence = calculate_match_confidence(
            doc_name="Weekly Standup",
            doc_created=now,
            event_summary="Weekly Standup",
            event_datetime=now,
            event_attendees=["user1@example.com", "user2@example.com"],
            transcript_speakers=["user1", "user2"],
        )
        # 名前1.0*0.4 + 時間1.0*0.3 + 参加者1.0*0.3 = 1.0
        assert confidence == pytest.approx(1.0, abs=0.01)

    def test_weight_distribution(self) -> None:
        """重み配分（0.4, 0.3, 0.3）の確認."""
        now = datetime.now()

        # 名前のみ一致（0.4）
        name_only = calculate_match_confidence(
            doc_name="Weekly Standup",
            doc_created=now - timedelta(hours=30),  # 24時間超 → 0
            event_summary="Weekly Standup",
            event_datetime=now,
            event_attendees=["user1@example.com"],
            transcript_speakers=["unknown"],  # 不一致 → 0
        )
        assert name_only == pytest.approx(0.4, abs=0.05)
