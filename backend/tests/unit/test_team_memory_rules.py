from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.entities.series import Occurrence
from src.domain.entities.team_memory import ActionItem, Decision, MemoryItem, OpenIssue, Resolution
from src.domain.services.team_memory_rules import carry_over_count, resolution_allowed

BASE = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("cancelled", "closed", "target", "now", "expected"),
    [
        (False, None, 3, 5, 2),
        (False, 2, 3, 5, 1),
        (True, None, 3, 5, 0),
        (False, None, 3, 2, 1),
        (False, None, 1, 5, 0),
        (False, 1, 4, 5, 0),
    ],
)
def test_carry_over_uses_strict_start_boundaries(
    cancelled: bool, closed: int | None, target: int, now: int, expected: int
) -> None:
    sid = uuid4()
    item = ActionItem(
        id=uuid4(),
        series_id=sid,
        body="Follow up",
        origin_occurrence_id=uuid4(),
        origin_start_at=BASE,
        extracted=False,
        closed_at=BASE + timedelta(days=closed) if closed is not None else None,
    )
    occurrences = [
        Occurrence(
            uuid4(), sid, BASE + timedelta(days=20), BASE + timedelta(days=i), cancelled, None, 0, None, 0, False
        )
        for i in range(4)
    ]
    assert carry_over_count(item, occurrences, BASE + timedelta(days=target), BASE + timedelta(days=now)) == expected


@pytest.mark.parametrize("kind", ["decision", "action_item", "open_issue"])
@pytest.mark.parametrize("resolution", [None, "reversed", "done", "dropped", "resolved"])
@pytest.mark.parametrize("creator", [True, False])
def test_resolution_kind_and_role_matrix(kind: str, resolution: Resolution | None, creator: bool) -> None:
    shared = {
        "id": uuid4(),
        "series_id": uuid4(),
        "origin_occurrence_id": uuid4(),
    }
    item: MemoryItem
    if kind == "decision":
        item = Decision(
            id=shared["id"],
            series_id=shared["series_id"],
            body="Item",
            origin_occurrence_id=shared["origin_occurrence_id"],
            origin_start_at=BASE,
            extracted=False,
        )
    elif kind == "action_item":
        item = ActionItem(
            id=shared["id"],
            series_id=shared["series_id"],
            body="Item",
            origin_occurrence_id=shared["origin_occurrence_id"],
            origin_start_at=BASE,
            extracted=False,
        )
    else:
        item = OpenIssue(
            id=shared["id"],
            series_id=shared["series_id"],
            body="Item",
            origin_occurrence_id=shared["origin_occurrence_id"],
            origin_start_at=BASE,
            extracted=False,
        )
    allowed = {
        "decision": {None, "reversed"},
        "action_item": {None, "done", "dropped"},
        "open_issue": {None, "resolved", "dropped"},
    }
    assert resolution_allowed(item, resolution, creator=creator) == (
        (creator or kind == "action_item") and resolution in allowed[kind]
    )
