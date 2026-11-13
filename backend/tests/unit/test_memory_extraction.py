import json
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

from src.config import settings
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import Attendee
from src.domain.entities.team_memory import ActionItem, Decision, NewActionItem
from src.infrastructure.external.bedrock_client import invoke_claude_tool
from src.infrastructure.services.meeting_memory_extractor import (
    MAX_INPUT_CHARS,
    RECORD_MEETING_MEMORY,
    ExtractionContext,
    build_extraction_prompt,
    parse_extraction,
)


def context() -> ExtractionContext:
    now, sid, oid = datetime.now(UTC), uuid4(), uuid4()
    action = ActionItem(
        id=uuid4(), series_id=sid, body="Follow up", origin_occurrence_id=oid, origin_start_at=now, extracted=True
    )
    decision = Decision(
        id=uuid4(),
        series_id=sid,
        body="Ship",
        origin_occurrence_id=oid,
        origin_start_at=now,
        extracted=False,
        human_updated_at=now,
    )
    return ExtractionContext(
        oid, "Weekly", now, (Attendee("member@example.com"),), (), (), {"A1": action, "D1": decision}, (decision,)
    )


def test_parse_drops_untrusted_references_and_invalid_assignment() -> None:
    ctx = context()
    extracted = parse_extraction(
        {
            "new_items": [
                {
                    "kind": "action_item",
                    "body": "Next step",
                    "assignee_email": "outsider@example.com",
                    "due_on": "not-a-date",
                },
                {"kind": "decision", "body": "Ship"},
                {"kind": "decision", "body": " "},
                {"kind": "invented", "body": "Ignore"},
                {"kind": "action_item", "body": "Next step"},
            ],
            "closures": [
                {"ref": "unknown", "resolution": "done"},
                {"ref": "D1", "resolution": "done"},
                {"ref": "A1", "resolution": "resolved"},
                {"ref": "A1", "resolution": "done"},
            ],
        },
        ctx,
    )
    assert len(extracted.new_items) == 1
    item = extracted.new_items[0]
    assert isinstance(item, NewActionItem) and item.assignee_email is None and item.due_on is None
    assert len(extracted.closures) == 1 and extracted.closures[0].item_id == ctx.references["A1"].id


def test_parse_normalizes_valid_attendee_and_date() -> None:
    extracted = parse_extraction(
        {
            "new_items": [
                {"kind": "action_item", "body": "Act", "assignee_email": "MEMBER@EXAMPLE.COM", "due_on": "2026-11-15"}
            ]
        },
        context(),
    )
    item = extracted.new_items[0]
    assert isinstance(item, NewActionItem) and item.assignee_email == "member@example.com"
    assert str(item.due_on) == "2026-11-15"


def test_complete_extraction_input_is_bounded_and_reported() -> None:
    ctx = context()
    source = Knowledge(
        uuid4(), uuid4(), ctx.occurrence_id, "upload", None, None, "x", "x" * (MAX_INPUT_CHARS + 1), ctx.start_at
    )
    prompt, truncated = build_extraction_prompt(replace(ctx, sources=(source,)))
    assert len(prompt) == MAX_INPUT_CHARS and truncated
    assert build_extraction_prompt(ctx)[1] is False


def test_tool_request_uses_configured_endpoint_and_forces_named_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AWS_BEARER_TOKEN_BEDROCK", "local")
    monkeypatch.setattr(settings, "AWS_BEDROCK_ENDPOINT", "http://bedrock.local")
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "tool_use", "name": "record_meeting_memory", "input": {"new_items": [], "closures": []}}
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handle))
    with patch("src.infrastructure.external.bedrock_client.httpx.Client", return_value=client):
        assert invoke_claude_tool("notes", RECORD_MEETING_MEMORY) == {"new_items": [], "closures": []}
    body = json.loads(requests[0].content)
    assert requests[0].url.host == "bedrock.local"
    assert body["tool_choice"] == {"type": "tool", "name": "record_meeting_memory"}
    assert body["tools"] == [RECORD_MEETING_MEMORY]
