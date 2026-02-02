"""定例MTGフィルタリングサービス.

AC6, AC7, AC8の条件を適用してカレンダーイベントをフィルタリングする。
"""

from datetime import UTC, datetime, timedelta

from src.infrastructure.external.google_calendar_client import (
    CalendarAttendee,
    CalendarEvent,
)


def is_valid_rrule(recurrence: list[str] | None) -> bool:
    """RRULEが定例MTGとして有効かを判定する.

    AC6: RRULEを持つイベントのみを検出対象とする。
    ただし、毎日（DAILY）は定例MTGとして対象外。

    Args:
        recurrence: RRULEリスト

    Returns:
        定例MTGとして有効な場合True
    """
    if not recurrence:
        return False

    for rule in recurrence:
        if not rule.startswith("RRULE:"):
            continue

        # 毎日は定例MTGとして対象外
        if "FREQ=DAILY" in rule:
            return False

        # 週次、月次のいずれかが含まれていれば有効
        if any(freq in rule for freq in ["FREQ=WEEKLY", "FREQ=MONTHLY"]):
            return True

    return False


def has_minimum_attendees(
    attendees: list[CalendarAttendee] | None,
    minimum: int = 2,
) -> bool:
    """参加者数が最低人数以上かを判定する.

    AC7: 参加者2人以上のイベントのみを検出対象とする。

    Args:
        attendees: 参加者リスト
        minimum: 最低参加者数（デフォルト: 2）

    Returns:
        最低人数以上の場合True
    """
    if attendees is None:
        return False
    return len(attendees) >= minimum


def has_recent_occurrence(
    last_occurrence: datetime,
    months: int = 3,
) -> bool:
    """指定月数以内に開催実績があるかを判定する.

    AC8: 過去3ヶ月以内に実績のあるイベントのみを検出対象とする。

    Args:
        last_occurrence: 最終開催日時
        months: 判定対象月数（デフォルト: 3）

    Returns:
        指定月数以内に実績がある場合True
    """
    now = datetime.now(UTC)
    # タイムゾーンがない場合はUTCとして扱う
    if last_occurrence.tzinfo is None:
        last_occurrence = last_occurrence.replace(tzinfo=UTC)
    threshold = now - timedelta(days=months * 30)
    return last_occurrence >= threshold


def parse_frequency_from_rrule(recurrence: list[str]) -> str:
    """RRULEから頻度を解析する.

    Args:
        recurrence: RRULEリスト

    Returns:
        頻度文字列（weekly, biweekly, monthly）
    """
    for rule in recurrence:
        if not rule.startswith("RRULE:"):
            continue

        if "FREQ=MONTHLY" in rule:
            return "monthly"
        if "FREQ=WEEKLY" in rule:
            if "INTERVAL=2" in rule:
                return "biweekly"
            return "weekly"

    return "weekly"  # デフォルト


class RecurringMeetingFilter:
    """定例MTGフィルタリングサービス.

    AC6, AC7, AC8の条件を適用してカレンダーイベントをフィルタリングする。
    """

    def __init__(
        self,
        min_attendees: int = 2,
        recent_months: int = 3,
    ) -> None:
        """フィルタを初期化する.

        Args:
            min_attendees: 最低参加者数
            recent_months: 判定対象月数
        """
        self.min_attendees = min_attendees
        self.recent_months = recent_months

    def filter_events(
        self,
        events: list[CalendarEvent],
    ) -> list[CalendarEvent]:
        """イベントをフィルタリングする.

        Args:
            events: カレンダーイベントリスト

        Returns:
            フィルタリング後のイベントリスト
        """
        return [event for event in events if self._is_valid_recurring_meeting(event)]

    def _is_valid_recurring_meeting(self, event: CalendarEvent) -> bool:
        """イベントが有効な定例MTGかを判定する."""
        # AC6: RRULEを持つイベントのみ
        if not is_valid_rrule(event.recurrence):
            return False

        # AC7: 参加者2人以上
        if not has_minimum_attendees(event.attendees, self.min_attendees):
            return False

        # AC8: 過去3ヶ月以内に実績あり
        return has_recent_occurrence(event.start, self.recent_months)
