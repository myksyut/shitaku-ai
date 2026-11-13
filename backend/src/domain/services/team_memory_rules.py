from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from src.domain.entities.series import Occurrence
from src.domain.entities.team_memory import RESOLUTIONS_BY_KIND, ActionItem, MemoryItem, OpenIssue, Resolution


def carry_over_count(
    item: ActionItem | OpenIssue, occurrences: Sequence[Occurrence], target_start: datetime, now: datetime
) -> int:
    """Count noncancelled meetings strictly between origin and target while open."""
    return sum(
        1
        for o in occurrences
        if not o.is_cancelled
        and item.origin_start_at < o.start_at < target_start
        and o.start_at < now
        and (item.closed_at is None or o.start_at < item.closed_at)
    )


def with_carry_over(
    items: Sequence[MemoryItem], occurrences: Sequence[Occurrence], target_start: datetime, now: datetime
) -> list[MemoryItem]:
    """Project derived counts without mutating stored memory."""
    return [
        replace(item, carry_over=carry_over_count(item, occurrences, target_start, now))
        if isinstance(item, ActionItem | OpenIssue)
        else item
        for item in items
    ]


def resolution_allowed(item: MemoryItem, resolution: Resolution | None, *, creator: bool) -> bool:
    """Keep the application check aligned with the database kind constraints."""
    return (creator or isinstance(item, ActionItem)) and (
        resolution is None or resolution in RESOLUTIONS_BY_KIND[item.kind]
    )
