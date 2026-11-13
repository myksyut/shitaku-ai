from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.domain.entities.agenda import AgendaTopic
from src.domain.entities.team_memory import ActionItem, OpenIssue
from src.domain.services.agenda_rules import render_agenda


@pytest.mark.parametrize("proposal", [None, "", "   ", "提案です"])
def test_required_sections_never_depend_on_model_output(proposal: str | None) -> None:
    now, sid, oid = datetime.now(UTC), uuid4(), uuid4()
    topics = [AgendaTopic(uuid4(), sid, oid, uuid4(), "招待客", f"議題{i}", f"詳細{i}", now) for i in range(3)]
    action = ActionItem(
        id=uuid4(),
        series_id=sid,
        body="確認する",
        origin_occurrence_id=oid,
        origin_start_at=now,
        extracted=True,
        assignee_email="member@example.com",
        due_on=date(2026, 11, 20),
        carry_over=2,
    )
    issue = OpenIssue(
        id=uuid4(),
        series_id=sid,
        body="設計を決める",
        origin_occurrence_id=oid,
        origin_start_at=now,
        extracted=False,
        carry_over=3,
    )
    content = render_agenda(topics, [action], [issue], proposal)
    assert content.startswith("## 事前に投稿された議題\n")
    for i in range(3):
        assert f"- 議題{i}（招待客）: 詳細{i}" in content
    assert "- 確認する（担当: member@example.com、期限: 2026-11-20）: 2回持ち越し" in content
    assert "- 設計を決める: 3回持ち越し" in content
    assert "## 議論の提案\n" in content
    if proposal and proposal.strip():
        assert content.endswith(proposal)
