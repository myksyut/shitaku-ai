from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError
from postgrest.types import JSON
from supabase import Client, create_client

from tests.rls.conftest import RlsEnvironment, RlsUser


@dataclass
class World:
    users: dict[str, RlsUser]
    sid: str
    oid: str
    past: str
    cancelled: str
    integration: str
    foreign_slack: str
    rows: dict[str, dict[str, JSON]]
    snapshot: dict[str, JSON]


@pytest.fixture
def world(
    make_user: Callable[[str], RlsUser], add_identity: Callable[[RlsUser, str, bool, str], None], service_client: Client
) -> Iterator[World]:
    users = {tag: make_user(tag) for tag in "ABCDE"}
    add_identity(users["B"], users["D"].email.upper(), True, "google")
    add_identity(users["E"], users["E"].email, False, "google")
    add_identity(users["D"], users["D"].email, True, "email")
    sid, oid, past, cancelled, integration, foreign_slack = (str(uuid4()) for _ in range(6))
    now = datetime.now(UTC)
    future = (now + timedelta(days=2)).isoformat()
    before = (now - timedelta(days=7)).isoformat()
    service_client.table("google_integrations").insert(
        {
            "id": integration,
            "user_id": str(users["A"].id),
            "email": users["A"].email,
            "encrypted_refresh_token": "secret",
        }
    ).execute()
    for tag, iid in (("A", str(uuid4())), ("C", foreign_slack)):
        service_client.table("slack_integrations").insert(
            {
                "id": iid,
                "user_id": str(users[tag].id),
                "workspace_id": iid,
                "workspace_name": "Private",
                "encrypted_access_token": "secret",
            }
        ).execute()
    snapshot: dict[str, JSON] = {
        "title": "Weekly",
        "rrule": "RRULE:FREQ=WEEKLY",
        "attendees_omitted": False,
        "attendees": [
            {
                "email": users["D"].email if tag == "B" else users[tag].email,
                "display_name": tag,
                "is_organizer": tag == "A",
            }
            for tag in ("A", "B", "E")
        ],
        "occurrences": [{"original_start": future, "start_at": future}],
        "window_start": (now - timedelta(days=35)).isoformat(),
        "window_end": (now + timedelta(days=35)).isoformat(),
    }
    service_client.table("series").insert(
        {
            "id": sid,
            "ical_uid": sid,
            "created_by": str(users["A"].id),
            "creator_event_id": "event",
            "google_integration_id": integration,
            "title": "Weekly",
            "calendar_synced_at": (now - timedelta(minutes=5)).isoformat(),
        }
    ).execute()
    try:
        service_client.rpc(
            "apply_calendar_snapshot",
            {
                "p_series_id": sid,
                "p_snapshot": snapshot,
                "p_fetched_at": now.isoformat(),
            },
        ).execute()
        service_client.table("occurrences").update({"id": oid}).eq("series_id", sid).execute()
        service_client.table("occurrences").insert(
            [
                {"id": past, "series_id": sid, "original_start": before, "start_at": before, "is_cancelled": False},
                {
                    "id": cancelled,
                    "series_id": sid,
                    "original_start": (now + timedelta(days=3)).isoformat(),
                    "start_at": future,
                    "is_cancelled": True,
                },
            ]
        ).execute()
        rows: dict[str, dict[str, JSON]] = {
            "agenda_topics": {
                "id": str(uuid4()),
                "series_id": sid,
                "occurrence_id": oid,
                "submitted_by": str(users["A"].id),
                "title": "A's topic",
            },
            "memory_items": {
                "id": str(uuid4()),
                "series_id": sid,
                "origin_occurrence_id": past,
                "kind": "action_item",
                "body": "Follow up",
                "extracted": False,
            },
            "knowledge": {
                "id": str(uuid4()),
                "series_id": sid,
                "occurrence_id": past,
                "source": "upload",
                "original_text": "Minutes",
                "normalized_text": "Minutes",
            },
            "agendas": {"occurrence_id": oid, "series_id": sid, "content": "Agenda", "generated_at": now.isoformat()},
            "dictionary_entries": {"id": str(uuid4()), "series_id": sid, "canonical_name": "Shitaku"},
        }
        for table, row in rows.items():
            service_client.table(table).insert(row).execute()
        yield World(users, sid, oid, past, cancelled, integration, foreign_slack, rows, snapshot)
    finally:
        service_client.table("series").delete().eq("id", sid).execute()


def denied(operation: Callable[[], object], code: str = "42501") -> None:
    try:
        result = operation()
    except APIError as error:
        assert error.code == code
    else:
        assert getattr(result, "data", None) == []


@pytest.mark.parametrize("tag", list("ABCDE"))
def test_table_crud_matrix(world: World, tag: str) -> None:
    client = world.users[tag].client
    roles = client.rpc("my_series_roles").execute().data
    assert roles == ([{"series_id": world.sid, "role": "creator" if tag == "A" else "member"}] if tag in "AB" else [])
    for table in ("series", "series_attendees", "occurrences", *world.rows, "occurrence_overview"):
        key = "id" if table == "series" else "series_id"
        result = client.table(table).select("*").eq(key, world.sid).execute()
        assert bool(result.data) == (tag in "AB"), (tag, table)
    for table in ("series_attendees", "occurrences"):
        row: dict[str, JSON] = (
            {"series_id": world.sid, "email": "forged@example.com"}
            if table == "series_attendees"
            else {
                "series_id": world.sid,
                "start_at": datetime.now(UTC).isoformat(),
                "original_start": datetime.now(UTC).isoformat(),
            }
        )
        denied(client.table(table).insert(row).execute)
        denied(client.table(table).update({"series_id": world.sid}).eq("series_id", world.sid).execute)
        denied(client.table(table).delete().eq("series_id", world.sid).execute)
    denied(
        lambda: client.table("series")
        .insert(
            {"ical_uid": str(uuid4()), "created_by": str(world.users[tag].id), "creator_event_id": "x", "title": "x"}
        )
        .execute()
    )
    denied(lambda: client.table("series").update({"ical_uid": "forged"}).eq("id", world.sid).execute())
    for table, original in world.rows.items():
        row = dict(original)
        row["occurrence_id" if table == "agendas" else "id"] = world.cancelled if table == "agendas" else str(uuid4())
        if table == "dictionary_entries":
            row["canonical_name"] = "New term"
        if table == "agenda_topics":
            row["submitted_by"] = str(world.users[tag].id)
            row.pop("id", None)
        can_insert = tag == "A" or (tag == "B" and table == "agenda_topics")
        if can_insert:
            assert client.table(table).insert(row).execute().data
        else:
            denied(client.table(table).insert(row).execute)
        field = {
            "agenda_topics": "title",
            "memory_items": "body",
            "knowledge": "normalized_text",
            "agendas": "content",
            "dictionary_entries": "description",
        }[table]
        if tag == "A" and table not in ("agenda_topics", "knowledge"):
            assert client.table(table).update({field: "Changed"}).eq("series_id", world.sid).execute().data
        else:
            denied(client.table(table).update({field: "Forged"}).eq("series_id", world.sid).execute)
        if tag == "A":
            assert client.table(table).delete().eq("series_id", world.sid).execute().data
        else:
            key = "occurrence_id" if table == "agendas" else "id"
            denied(client.table(table).delete().eq(key, str(original[key])).execute)
    if tag == "A":
        assert client.table("series").update({"description": "Changed"}).eq("id", world.sid).execute().data
        assert client.table("series").delete().eq("id", world.sid).execute().data
    else:
        denied(lambda: client.table("series").update({"description": "Forged"}).eq("id", world.sid).execute())
        denied(lambda: client.table("series").delete().eq("id", world.sid).execute())


@pytest.mark.parametrize("tag", list("ABCDE"))
def test_resolution_rpc_and_service_only_functions(world: World, tag: str, service_client: Client) -> None:
    client = world.users[tag].client
    denied(
        client.rpc(
            "mark_calendar_event_missing",
            {
                "p_series_id": world.sid,
                "p_fetched_at": datetime.now(UTC).isoformat(),
            },
        ).execute
    )
    action = str(world.rows["memory_items"]["id"])
    decision = str(uuid4())
    service_client.table("memory_items").insert(
        {
            "id": decision,
            "series_id": world.sid,
            "origin_occurrence_id": world.past,
            "kind": "decision",
            "body": "Ship it",
            "extracted": False,
        }
    ).execute()
    for iid, resolution in ((action, "done"), (decision, "reversed")):
        call = client.rpc("set_memory_item_resolution", {"p_item_id": iid, "p_resolution": resolution}).execute
        if tag == "A" or (tag == "B" and iid == action):
            assert call().data
        else:
            denied(call, "42501" if tag == "B" else "P0002")
    denied(
        lambda: client.rpc(
            "apply_calendar_snapshot",
            {
                "p_series_id": world.sid,
                "p_snapshot": world.snapshot,
                "p_fetched_at": datetime.now(UTC).isoformat(),
            },
        ).execute()
    )
    denied(
        lambda: client.rpc(
            "claim_series",
            {
                "p_creator_id": str(world.users[tag].id),
                "p_integration_id": world.integration,
                "p_snapshot": world.snapshot,
                "p_fetched_at": datetime.now(UTC).isoformat(),
            },
        ).execute()
    )
    if tag != "A":
        denied(
            lambda: client.rpc(
                "apply_extraction",
                {
                    "p_occurrence_id": world.past,
                    "p_items": [],
                    "p_closures": [],
                    "p_input_at": datetime.now(UTC).isoformat(),
                },
            ).execute(),
            "P0002",
        )


def test_topics_timing_authorship_and_delete(world: World) -> None:
    from pydantic import TypeAdapter

    member = world.users["B"]
    for oid in (world.past, world.cancelled):
        denied(
            member.client.table("agenda_topics")
            .insert({"series_id": world.sid, "occurrence_id": oid, "submitted_by": str(member.id), "title": "Too late"})
            .execute
        )
    denied(
        lambda: member.client.table("agenda_topics")
        .insert(
            {
                "series_id": world.sid,
                "occurrence_id": world.oid,
                "submitted_by": str(world.users["A"].id),
                "title": "Impersonation",
            }
        )
        .execute()
    )
    topic = (
        member.client.table("agenda_topics")
        .insert(
            {
                "series_id": world.sid,
                "occurrence_id": world.oid,
                "submitted_by": str(member.id),
                "title": "Member topic",
            }
        )
        .execute()
        .data[0]
    )
    assert topic
    topic_id = str(TypeAdapter(dict[str, JSON]).validate_python(topic)["id"])
    assert member.client.table("agenda_topics").delete().eq("id", topic_id).execute().data


def test_credentials_private_and_composite_binding(world: World) -> None:
    for tag in "BCDE":
        for table in ("google_integrations", "slack_integrations", "oauth_states"):
            assert (
                world.users[tag].client.table(table).select("*").eq("user_id", str(world.users["A"].id)).execute().data
                == []
            )
    with pytest.raises(APIError) as error:
        world.users["A"].client.table("series").update({"slack_integration_id": world.foreign_slack}).eq(
            "id", world.sid
        ).execute()
    assert error.value.code == "23503"


def test_snapshot_revocation_freshness_and_disconnect(world: World, service_client: Client) -> None:
    newer = datetime.now(UTC) + timedelta(seconds=2)
    snapshot: dict[str, JSON] = {**world.snapshot, "attendees": []}
    service_client.rpc(
        "apply_calendar_snapshot", {"p_series_id": world.sid, "p_snapshot": snapshot, "p_fetched_at": newer.isoformat()}
    ).execute()
    assert world.users["B"].client.table("series").select("id").eq("id", world.sid).execute().data == []
    service_client.rpc(
        "apply_calendar_snapshot",
        {
            "p_series_id": world.sid,
            "p_snapshot": world.snapshot,
            "p_fetched_at": (newer - timedelta(seconds=1)).isoformat(),
        },
    ).execute()
    assert world.users["B"].client.rpc("my_series_roles").execute().data == []
    service_client.table("google_integrations").delete().eq("id", world.integration).execute()
    series = world.users["A"].client.table("series").select("google_integration_id").eq("id", world.sid).execute().data
    assert series == [{"google_integration_id": None}]


def test_extraction_is_idempotent_and_human_edits_are_sticky(world: World, service_client: Client) -> None:
    from pydantic import TypeAdapter

    owner = world.users["A"].client
    input_at = datetime.now(UTC)
    items = [
        {"kind": "action_item", "body": "Extracted action", "extraction_key": "action-key"},
        {"kind": "open_issue", "body": "Temporary issue", "extraction_key": "issue-key"},
    ]
    arguments = {"p_occurrence_id": world.past, "p_items": items, "p_closures": [], "p_input_at": input_at.isoformat()}
    assert owner.rpc("apply_extraction", arguments).execute().data == {"created": 2, "closed": 0}
    before = owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    assert owner.rpc("apply_extraction", arguments).execute().data == {"created": 0, "closed": 0}
    assert owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data == before
    owner.table("memory_items").update({"body": "Human correction", "human_updated_at": input_at.isoformat()}).eq(
        "series_id", world.sid
    ).eq("extraction_key", "action-key").execute()
    owner.rpc("apply_extraction", {**arguments, "p_items": []}).execute()
    assert owner.table("memory_items").select("body").eq("series_id", world.sid).eq(
        "extraction_key", "action-key"
    ).execute().data == [{"body": "Human correction"}]
    assert (
        owner.table("memory_items")
        .select("id")
        .eq("series_id", world.sid)
        .eq("extraction_key", "issue-key")
        .execute()
        .data
        != []
    )
    service_client.table("knowledge").insert(
        {
            "series_id": world.sid,
            "occurrence_id": world.past,
            "source": "upload",
            "original_text": "Concurrent",
            "normalized_text": "Concurrent",
            "created_at": (input_at + timedelta(seconds=1)).isoformat(),
        }
    ).execute()
    overview = (
        owner.table("occurrence_overview")
        .select("extracted_at,latest_knowledge_at")
        .eq("series_id", world.sid)
        .eq("id", world.past)
        .execute()
        .data
    )
    assert TypeAdapter(list[dict[str, datetime]]).validate_python(overview) == [
        {"extracted_at": input_at, "latest_knowledge_at": input_at + timedelta(seconds=1)}
    ]


@pytest.mark.parametrize("tag", ["B", "C"])
def test_member_and_outsider_extraction_cannot_change_any_state(world: World, tag: str, service_client: Client) -> None:
    before_items = (
        service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    )
    before_occurrences = (
        service_client.table("occurrences").select("*").eq("series_id", world.sid).order("id").execute().data
    )
    denied(
        lambda: world.users[tag]
        .client.rpc(
            "apply_extraction",
            {
                "p_occurrence_id": world.past,
                "p_items": [{"kind": "decision", "body": "Forged", "extraction_key": "forged"}],
                "p_closures": [{"item_id": str(world.rows["memory_items"]["id"]), "resolution": "done"}],
                "p_input_at": datetime.now(UTC).isoformat(),
            },
        )
        .execute(),
        "P0002",
    )
    assert (
        service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
        == before_items
    )
    assert (
        service_client.table("occurrences").select("*").eq("series_id", world.sid).order("id").execute().data
        == before_occurrences
    )


async def test_memory_repository_maps_real_composite_origin_join(world: World) -> None:
    from uuid import UUID

    from src.infrastructure.repositories.team_memory_repository_impl import TeamMemoryRepositoryImpl

    items = await TeamMemoryRepositoryImpl(world.users["B"].client).list_items(UUID(world.sid))
    assert len(items) == 1 and items[0].kind == "action_item"
    assert items[0].origin_occurrence_id == UUID(world.past)


@pytest.fixture
def bedrock_extraction_payload() -> dict[str, JSON]:
    return {"new_items": [{"kind": "decision", "body": "Extracted through real HTTP"}], "closures": []}


@pytest.fixture
def bedrock_stub(monkeypatch: pytest.MonkeyPatch, bedrock_extraction_payload: dict[str, JSON]) -> Iterator[str]:
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from src.config import settings

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "tools" in payload:
                content = [
                    {
                        "type": "tool_use",
                        "name": "record_meeting_memory",
                        "input": bedrock_extraction_payload,
                    }
                ]
            elif payload["max_tokens"] == 2048:
                content = [
                    {
                        "type": "text",
                        "text": json.dumps({"normalized_text": "Normalized meeting notes", "replacements": []}),
                    }
                ]
            else:
                content = [{"type": "text", "text": ""}]
            data = json.dumps({"content": content}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(settings, "AWS_BEARER_TOKEN_BEDROCK", "local-stub")
    monkeypatch.setattr(settings, "AWS_BEDROCK_ENDPOINT", url)
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_real_http_member_topic_creator_agenda_memory_and_dictionary(
    world: World,
    service_client: Client,
    bedrock_stub: str,
) -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    assert bedrock_stub.startswith("http://127.0.0.1:")
    service_client.table("series").update({"google_integration_id": None}).eq("id", world.sid).execute()
    middle = datetime.now(UTC) - timedelta(days=2)
    service_client.table("occurrences").insert(
        {"series_id": world.sid, "start_at": middle.isoformat(), "original_start": middle.isoformat()}
    ).execute()
    headers = {tag: {"Authorization": f"Bearer {user.access_token}"} for tag, user in world.users.items()}
    base = f"/api/v1/series/{world.sid}"
    occurrence = f"{base}/occurrences/{world.oid}"
    with TestClient(app) as api:
        assert api.get(base, headers=headers["C"]).status_code == 404
        assert api.get("/api/v1/series", headers=headers["B"]).json()["series"][0]["role"] == "member"
        assert api.post(f"{occurrence}/agenda", headers=headers["B"]).status_code == 403
        assert (
            api.post(
                f"{occurrence}/knowledge", json={"source": "upload", "text": "forged"}, headers=headers["B"]
            ).status_code
            == 403
        )
        topic = api.post(
            f"{occurrence}/topics",
            json={"title": "Member's required topic", "details": "Must remain"},
            headers=headers["B"],
        )
        assert topic.status_code == 201, topic.text
        assert topic.json()["is_mine"] is True
        generated = api.post(f"{occurrence}/agenda", headers=headers["A"])
        assert generated.status_code == 200, generated.text
        agenda = generated.json()
        assert "Member's required topic" in agenda["agenda"]["content"]
        assert "Follow up" in agenda["agenda"]["content"]
        assert "1回持ち越し" in agenda["agenda"]["content"]
        assert agenda["sources"]["topics"] == 2
        assert agenda["sources"]["carried_action_items"] == 1
        assert agenda["sources"]["calendar_error"] == "not_connected"
        assert api.get(base, headers=headers["B"]).json()["calendar"]["error"] == "not_connected"
        assert (
            api.get("/api/v1/series", headers=headers["B"]).json()["series"][0]["calendar_sync_error"]
            == "not_connected"
        )
        assert "series_id" not in agenda["agenda"]
        edited = api.put(f"{occurrence}/agenda", json={"content": "Creator edit"}, headers=headers["A"])
        assert edited.status_code == 200
        assert api.get(occurrence, headers=headers["B"]).json()["agenda"]["content"] == "Creator edit"
        dictionary = api.post(
            f"{base}/dictionary",
            json={"canonical_name": "Shared term", "category": "term", "aliases": ["alias"], "description": "Context"},
            headers=headers["A"],
        )
        assert dictionary.status_code == 201, dictionary.text
        eid = dictionary.json()["id"]
        assert api.put(f"{base}/dictionary/{eid}", json={"description": None}, headers=headers["B"]).status_code == 403
        updated = api.put(f"{base}/dictionary/{eid}", json={"description": None}, headers=headers["A"])
        assert updated.status_code == 200 and updated.json()["aliases"] == ["alias"]
        assert len(api.get(f"{base}/dictionary", headers=headers["B"]).json()) == 2
        upload = api.post(
            f"{base}/occurrences/{world.past}/knowledge",
            json={"source": "upload", "text": "Raw notes"},
            headers=headers["A"],
        )
        assert upload.status_code == 201, upload.text
        kid = upload.json()["knowledge"]["id"]
        assert api.get(f"{base}/knowledge/{kid}", headers=headers["B"]).json()["text"] == "Normalized meeting notes"
        extraction = api.post(f"{base}/occurrences/{world.past}/extract", headers=headers["A"])
        assert extraction.status_code == 200, extraction.text
        assert extraction.json()["created"] == 1 and extraction.json()["truncated"] is False
        assert api.post(f"{base}/occurrences/{world.past}/extract", headers=headers["A"]).json()["created"] == 0
        manual = api.post(
            f"{base}/memory",
            json={"kind": "open_issue", "body": "Human issue", "origin_occurrence_id": world.past},
            headers=headers["A"],
        )
        assert manual.status_code == 201, manual.text
        manual_id = next(i["id"] for i in manual.json()["items"] if i["body"] == "Human issue")
        update = api.put(
            f"{base}/memory/{manual_id}",
            json={"kind": "open_issue", "body": "Edited issue", "origin_occurrence_id": world.past},
            headers=headers["A"],
        )
        assert update.status_code == 200, update.text
        wrong_kind = api.put(
            f"{base}/memory/{manual_id}",
            json={"kind": "decision", "body": "Changed kind", "origin_occurrence_id": world.past},
            headers=headers["A"],
        )
        assert wrong_kind.status_code == 422
        assert api.delete(f"{base}/memory/{manual_id}", headers=headers["A"]).status_code == 200
        action_id = str(world.rows["memory_items"]["id"])
        resolution = api.put(f"{base}/memory/{action_id}/resolution", json={"resolution": "done"}, headers=headers["B"])
        assert resolution.status_code == 200, resolution.text
        assert any(i["id"] == action_id and i["resolution"] == "done" for i in resolution.json()["items"])
        assert all("series_id" not in i and "human_updated_at" not in i for i in resolution.json()["items"])
        assert api.delete(f"{base}/dictionary/{eid}", headers=headers["A"]).status_code == 204
        assert api.delete(f"{base}/knowledge/{kid}", headers=headers["A"]).status_code == 204
        assert api.delete(f"{base}/topics/{topic.json()['id']}", headers=headers["B"]).status_code == 204


def test_resolution_reopen_protects_human_choice_from_extraction(world: World) -> None:
    action = str(world.rows["memory_items"]["id"])
    for resolution in ("done", None):
        world.users["B"].client.rpc(
            "set_memory_item_resolution", {"p_item_id": action, "p_resolution": resolution}
        ).execute()
    result = (
        world.users["A"]
        .client.rpc(
            "apply_extraction",
            {
                "p_occurrence_id": world.past,
                "p_items": [],
                "p_closures": [{"item_id": action, "resolution": "done"}],
                "p_input_at": datetime.now(UTC).isoformat(),
            },
        )
        .execute()
        .data
    )
    assert result == {"created": 0, "closed": 0}
    assert world.users["B"].client.table("memory_items").select("resolution,closed_at").eq("series_id", world.sid).eq(
        "id", action
    ).execute().data == [{"resolution": None, "closed_at": None}]


def test_database_resolution_constraints_match_all_variants(world: World, service_client: Client) -> None:
    allowed = {"decision": {"reversed"}, "action_item": {"done", "dropped"}, "open_issue": {"resolved", "dropped"}}
    for kind, resolutions in allowed.items():
        for resolution in ("reversed", "done", "dropped", "resolved"):
            payload: dict[str, JSON] = {
                "series_id": world.sid,
                "origin_occurrence_id": world.past,
                "kind": kind,
                "body": "Constraint",
                "extracted": False,
                "resolution": resolution,
                "closed_at": datetime.now(UTC).isoformat(),
            }
            if resolution in resolutions:
                assert service_client.table("memory_items").insert(payload).execute().data
            else:
                with pytest.raises(APIError) as error:
                    service_client.table("memory_items").insert(payload).execute()
                assert error.value.code == "23514"


def test_anonymous_cannot_read_team_tables_or_call_team_rpcs(world: World, rls_env: RlsEnvironment) -> None:
    anonymous = create_client(rls_env.SUPABASE_URL, rls_env.SUPABASE_ANON_KEY)
    for table in ("series", "series_attendees", "occurrences", *world.rows, "occurrence_overview"):
        denied(anonymous.table(table).select("*").execute)
    denied(anonymous.rpc("my_series_roles").execute)
    denied(
        anonymous.rpc(
            "set_memory_item_resolution",
            {
                "p_item_id": str(world.rows["memory_items"]["id"]),
                "p_resolution": "done",
            },
        ).execute
    )
    denied(
        anonymous.rpc(
            "apply_extraction",
            {
                "p_occurrence_id": world.past,
                "p_items": [],
                "p_closures": [],
                "p_input_at": datetime.now(UTC).isoformat(),
            },
        ).execute
    )
    denied(
        anonymous.rpc(
            "apply_calendar_snapshot",
            {"p_series_id": world.sid, "p_snapshot": world.snapshot, "p_fetched_at": datetime.now(UTC).isoformat()},
        ).execute
    )


def test_service_claim_is_atomic_and_duplicate_claim_does_not_apply_joiners_snapshot(
    world: World,
    service_client: Client,
) -> None:
    from pydantic import TypeAdapter

    ical_uid = str(uuid4())
    arguments = {
        "p_creator_id": str(world.users["A"].id),
        "p_integration_id": world.integration,
        "p_snapshot": {**world.snapshot, "ical_uid": ical_uid, "event_id": "new-creator-id"},
        "p_fetched_at": datetime.now(UTC).isoformat(),
    }
    try:
        first = TypeAdapter(list[dict[str, JSON]]).validate_python(
            service_client.rpc("claim_series", arguments).execute().data
        )
        assert first[0]["created"] is True
        second = TypeAdapter(list[dict[str, JSON]]).validate_python(
            service_client.rpc(
                "claim_series",
                {
                    **arguments,
                    "p_snapshot": {
                        **world.snapshot,
                        "ical_uid": ical_uid,
                        "event_id": "imported",
                        "title": "Forged title",
                        "attendees": [],
                    },
                },
            )
            .execute()
            .data
        )
        assert second[0]["created"] is False and second[0]["series_id"] == first[0]["series_id"]
        sid = str(first[0]["series_id"])
        assert world.users["B"].client.table("series").select("title,creator_event_id").eq(
            "id", sid
        ).execute().data == [{"title": "Weekly", "creator_event_id": "new-creator-id"}]
        assert service_client.table("occurrences").select("id").eq("series_id", sid).execute().data
    finally:
        service_client.table("series").delete().eq("ical_uid", ical_uid).execute()


def test_omitted_guest_snapshot_keeps_last_trusted_membership(world: World, service_client: Client) -> None:
    service_client.rpc(
        "apply_calendar_snapshot",
        {
            "p_series_id": world.sid,
            "p_snapshot": {**world.snapshot, "attendees_omitted": True, "attendees": []},
            "p_fetched_at": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
        },
    ).execute()
    assert world.users["B"].client.table("series").select("calendar_sync_error").eq("id", world.sid).execute().data == [
        {"calendar_sync_error": "attendees_omitted"}
    ]


def test_calendar_error_constraint_accepts_only_public_codes(world: World, service_client: Client) -> None:
    codes = (
        "not_connected",
        "scope_missing",
        "revoked",
        "attendees_omitted",
        "event_not_found",
        "calendar_unavailable",
    )
    for code in (*codes, None):
        service_client.table("series").update({"calendar_sync_error": code}).eq("id", world.sid).execute()
        assert world.users["B"].client.table("series").select("calendar_sync_error").eq(
            "id", world.sid
        ).execute().data == [{"calendar_sync_error": code}]
    with pytest.raises(APIError) as error:
        service_client.table("series").update({"calendar_sync_error": "Google integration not connected"}).eq(
            "id", world.sid
        ).execute()
    assert error.value.code == "23514"


def test_out_of_order_extraction_cannot_overwrite_newer_state(world: World) -> None:
    from pydantic import TypeAdapter

    owner = world.users["A"].client
    newer = datetime.now(UTC)
    arguments = {
        "p_occurrence_id": world.past,
        "p_input_at": newer.isoformat(),
        "p_items": [{"kind": "decision", "body": "Newer result", "extraction_key": "newer"}],
        "p_closures": [],
    }
    assert owner.rpc("apply_extraction", arguments).execute().data == {"created": 1, "closed": 0}
    before = owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    stale = (
        owner.rpc(
            "apply_extraction",
            {
                **arguments,
                "p_input_at": (newer - timedelta(seconds=1)).isoformat(),
                "p_items": [{"kind": "decision", "body": "Older result", "extraction_key": "older"}],
                "p_closures": [{"item_id": str(world.rows["memory_items"]["id"]), "resolution": "done"}],
            },
        )
        .execute()
        .data
    )
    assert stale == {"created": 0, "closed": 0, "stale": True}
    assert owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data == before
    marker = (
        owner.table("occurrences").select("extracted_at").eq("series_id", world.sid).eq("id", world.past).execute().data
    )
    assert TypeAdapter(list[dict[str, datetime]]).validate_python(marker) == [{"extracted_at": newer}]


def test_stale_extraction_http_returns_conflict_without_changes(
    world: World,
    service_client: Client,
    bedrock_stub: str,
) -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    assert bedrock_stub.startswith("http://127.0.0.1:")
    future = datetime.now(UTC) + timedelta(minutes=1)
    service_client.table("occurrences").update({"extracted_at": future.isoformat()}).eq("series_id", world.sid).eq(
        "id", world.past
    ).execute()
    before = service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    with TestClient(app) as api:
        response = api.post(
            f"/api/v1/series/{world.sid}/occurrences/{world.past}/extract",
            headers={"Authorization": f"Bearer {world.users['A'].access_token}"},
        )
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "stale_extraction"}
    assert (
        service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data == before
    )


def test_reextraction_closes_same_occurrence_items_before_replacing_them(world: World) -> None:
    from pydantic import TypeAdapter

    owner = world.users["A"].client
    input_at = datetime.now(UTC).isoformat()
    arguments = {
        "p_occurrence_id": world.past,
        "p_input_at": input_at,
        "p_closures": [],
        "p_items": [
            {"kind": "action_item", "body": "Action resolved during this meeting", "extraction_key": "same-occurrence"}
        ],
    }
    assert owner.rpc("apply_extraction", arguments).execute().data == {"created": 1, "closed": 0}
    rows = (
        owner.table("memory_items")
        .select("id")
        .eq("series_id", world.sid)
        .eq("extraction_key", "same-occurrence")
        .execute()
        .data
    )
    item_id = TypeAdapter(list[dict[str, str]]).validate_python(rows)[0]["id"]
    closures = {**arguments, "p_items": [], "p_closures": [{"item_id": item_id, "resolution": "done"}]}
    assert owner.rpc("apply_extraction", closures).execute().data == {"created": 0, "closed": 1}
    assert owner.table("memory_items").select("id,resolution,human_updated_at").eq("series_id", world.sid).eq(
        "id", item_id
    ).execute().data == [{"id": item_id, "resolution": "done", "human_updated_at": None}]
    assert owner.rpc("apply_extraction", closures).execute().data == {"created": 0, "closed": 0}
    assert owner.table("memory_items").select("id").eq("series_id", world.sid).eq("id", item_id).execute().data == [
        {"id": item_id}
    ]


@pytest.mark.parametrize("state", ["untouched", "human_edited", "closed", "manual"])
def test_reextraction_corrects_only_untouched_open_extracted_metadata(
    world: World,
    service_client: Client,
    state: str,
) -> None:
    from pydantic import TypeAdapter

    owner = world.users["A"].client
    input_at = datetime.now(UTC)
    original: dict[str, JSON] = {
        "kind": "action_item",
        "body": "Stable action body",
        "extraction_key": "stable-action",
        "assignee_email": None,
        "due_on": "2026-11-20",
    }
    arguments = {
        "p_occurrence_id": world.past,
        "p_input_at": input_at.isoformat(),
        "p_items": [original],
        "p_closures": [],
    }
    assert owner.rpc("apply_extraction", arguments).execute().data == {"created": 1, "closed": 0}
    rows = (
        owner.table("memory_items")
        .select("id")
        .eq("series_id", world.sid)
        .eq("extraction_key", "stable-action")
        .execute()
        .data
    )
    item_id = TypeAdapter(list[dict[str, str]]).validate_python(rows)[0]["id"]
    if state == "human_edited":
        service_client.table("memory_items").update({"human_updated_at": input_at.isoformat()}).eq(
            "series_id", world.sid
        ).eq("id", item_id).execute()
    elif state == "closed":
        service_client.table("memory_items").update({"resolution": "done", "closed_at": input_at.isoformat()}).eq(
            "series_id", world.sid
        ).eq("id", item_id).execute()
    elif state == "manual":
        service_client.table("memory_items").update({"extracted": False}).eq("series_id", world.sid).eq(
            "id", item_id
        ).execute()
    corrected = {**original, "assignee_email": world.users["D"].email, "due_on": "2026-12-20"}
    updated = {**arguments, "p_input_at": (input_at + timedelta(seconds=1)).isoformat(), "p_items": [corrected]}
    assert owner.rpc("apply_extraction", updated).execute().data == {"created": 0, "closed": 0}
    expected_assignee = world.users["D"].email.lower() if state == "untouched" else None
    expected_due = "2026-12-20" if state == "untouched" else "2026-11-20"
    assert owner.table("memory_items").select("id,assignee_email,due_on").eq("series_id", world.sid).eq(
        "id", item_id
    ).execute().data == [{"id": item_id, "assignee_email": expected_assignee, "due_on": expected_due}]
    assert owner.rpc("apply_extraction", updated).execute().data == {"created": 0, "closed": 0}
    if state == "untouched":
        cleared = {**updated, "p_items": [{**original, "due_on": None}]}
        assert owner.rpc("apply_extraction", cleared).execute().data == {"created": 0, "closed": 0}
        assert owner.table("memory_items").select("id,assignee_email,due_on").eq("series_id", world.sid).eq(
            "id", item_id
        ).execute().data == [{"id": item_id, "assignee_email": None, "due_on": None}]


def test_malformed_extraction_http_cannot_delete_existing_extracted_memory(
    world: World,
    service_client: Client,
    bedrock_stub: str,
    bedrock_extraction_payload: dict[str, JSON],
) -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    assert bedrock_stub.startswith("http://127.0.0.1:")
    owner = world.users["A"].client
    owner.rpc(
        "apply_extraction",
        {
            "p_occurrence_id": world.past,
            "p_input_at": datetime.now(UTC).isoformat(),
            "p_items": [{"kind": "open_issue", "body": "Must survive malformed output", "extraction_key": "preserved"}],
            "p_closures": [],
        },
    ).execute()
    before = service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    marker = (
        service_client.table("occurrences")
        .select("extracted_at")
        .eq("series_id", world.sid)
        .eq("id", world.past)
        .execute()
        .data
    )
    malformed: list[dict[str, JSON]] = [
        {"new_items": [{}], "closures": []},
        {"new_items": [{"kind": "decision", "body": "Valid"}, {}], "closures": []},
        {"new_items": [{"kind": "unknown", "body": "Invalid"}], "closures": []},
        {"new_items": [{"kind": "decision", "body": ""}], "closures": []},
        {"new_items": [None], "closures": []},
        {"new_items": [], "closures": [{}]},
        {"new_items": [], "closures": [123]},
        {"new_items": [], "closures": [{"ref": "unknown", "resolution": "invented"}]},
    ]
    with TestClient(app) as api:
        for payload in malformed:
            bedrock_extraction_payload.clear()
            bedrock_extraction_payload.update(payload)
            response = api.post(
                f"/api/v1/series/{world.sid}/occurrences/{world.past}/extract",
                headers={"Authorization": f"Bearer {world.users['A'].access_token}"},
            )
            assert response.status_code == 502, response.text
            assert response.json() == {"detail": "Memory extraction unavailable"}
            assert (
                service_client.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
                == before
            )
            assert (
                service_client.table("occurrences")
                .select("extracted_at")
                .eq("series_id", world.sid)
                .eq("id", world.past)
                .execute()
                .data
                == marker
            )


def test_calendar_snapshot_cancels_missing_slots_only_inside_fetched_window(
    world: World, service_client: Client
) -> None:
    from pydantic import TypeAdapter

    original = TypeAdapter(list[dict[str, str]]).validate_python(world.snapshot["occurrences"])[0]["original_start"]
    base = datetime.fromisoformat(original) - timedelta(days=2)
    outside = base + timedelta(days=10)
    service_client.table("occurrences").insert(
        {"series_id": world.sid, "original_start": outside.isoformat(), "start_at": outside.isoformat()}
    ).execute()
    snapshot = {
        **world.snapshot,
        "window_start": (base + timedelta(days=1)).isoformat(),
        "window_end": (base + timedelta(days=5)).isoformat(),
        "occurrences": [
            {
                "original_start": (base + timedelta(days=d)).isoformat(),
                "start_at": (base + timedelta(days=d)).isoformat(),
            }
            for d in (2, 3)
        ],
    }
    service_client.rpc(
        "apply_calendar_snapshot",
        {
            "p_series_id": world.sid,
            "p_snapshot": snapshot,
            "p_fetched_at": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
        },
    ).execute()
    snapshot["occurrences"] = [
        {"original_start": (base + timedelta(days=d)).isoformat(), "start_at": (base + timedelta(days=d)).isoformat()}
        for d in (3, 4)
    ]
    service_client.rpc(
        "apply_calendar_snapshot",
        {
            "p_series_id": world.sid,
            "p_snapshot": snapshot,
            "p_fetched_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat(),
        },
    ).execute()
    for days, cancelled in ((2, True), (3, False), (4, False), (10, False)):
        assert world.users["B"].client.table("occurrences").select("is_cancelled").eq("series_id", world.sid).eq(
            "original_start", (base + timedelta(days=days)).isoformat()
        ).execute().data == [{"is_cancelled": cancelled}]
    assert (
        world.users["B"]
        .client.table("agenda_topics")
        .select("id")
        .eq("series_id", world.sid)
        .eq("occurrence_id", world.oid)
        .execute()
        .data
    )
    assert world.users["B"].client.table("occurrences").select("is_cancelled").eq("series_id", world.sid).eq(
        "id", world.past
    ).execute().data == [{"is_cancelled": False}]


async def test_missing_creator_calendar_event_cancels_all_future_occurrences(
    world: World, service_client: Client
) -> None:
    from unittest.mock import AsyncMock, MagicMock
    from uuid import UUID

    from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
    from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials
    from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl

    series = await SeriesRepositoryImpl(world.users["A"].client).get(UUID(world.sid))
    assert series is not None
    credentials, calendar = AsyncMock(spec=SeriesCredentials), AsyncMock()
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    calendar.snapshot.return_value = None
    assert await SeriesCalendarMirror(service_client, credentials).refresh(series) == "event_not_found"
    assert world.users["B"].client.table("occurrences").select("is_cancelled").eq("series_id", world.sid).eq(
        "id", world.oid
    ).execute().data == [{"is_cancelled": True}]
    assert world.users["B"].client.table("occurrences").select("is_cancelled").eq("series_id", world.sid).eq(
        "id", world.past
    ).execute().data == [{"is_cancelled": False}]


def test_creator_relinks_google_after_disconnect_with_owned_calendar_scope(
    world: World, service_client: Client
) -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    service_client.table("google_integrations").delete().eq("id", world.integration).execute()
    reconnected, foreign, no_scope = (str(uuid4()) for _ in range(3))
    for iid, tag, scopes in (
        (reconnected, "A", ["https://www.googleapis.com/auth/calendar.readonly"]),
        (foreign, "C", ["https://www.googleapis.com/auth/calendar.readonly"]),
        (no_scope, "A", []),
    ):
        service_client.table("google_integrations").insert(
            {
                "id": iid,
                "user_id": str(world.users[tag].id),
                "email": f"{iid}@example.com",
                "encrypted_refresh_token": "not-needed-for-scope-validation",
                "granted_scopes": scopes,
            }
        ).execute()
    settings = {
        "description": None,
        "minutes_count": 3,
        "slack_message_days": 7,
        "slack": None,
        "google_integration_id": reconnected,
    }
    headers = {tag: {"Authorization": f"Bearer {user.access_token}"} for tag, user in world.users.items()}
    base = f"/api/v1/series/{world.sid}"
    with TestClient(app) as api:
        before = api.get(base, headers=headers["B"]).json()["calendar"]
        assert before["integration_id"] is None and before["google_connected"] is False
        assert api.put(f"{base}/settings", json=settings, headers=headers["B"]).status_code == 403
        assert api.put(f"{base}/settings", json=settings, headers=headers["C"]).status_code == 404
        missing_scope = api.put(
            f"{base}/settings", json={**settings, "google_integration_id": no_scope}, headers=headers["A"]
        )
        assert missing_scope.status_code == 409 and missing_scope.json()["detail"] == "scope_missing"
        foreign_binding = api.put(
            f"{base}/settings", json={**settings, "google_integration_id": foreign}, headers=headers["A"]
        )
        assert foreign_binding.status_code == 409 and foreign_binding.json()["detail"] == "not_connected"
        relinked = api.put(f"{base}/settings", json=settings, headers=headers["A"])
        assert relinked.status_code == 200, relinked.text
        assert relinked.json()["calendar"]["integration_id"] == reconnected
        assert relinked.json()["calendar"]["google_connected"] is True
        cleared = api.put(f"{base}/settings", json={**settings, "google_integration_id": None}, headers=headers["A"])
        assert cleared.status_code == 200
        assert cleared.json()["calendar"]["integration_id"] is None
        assert cleared.json()["calendar"]["google_connected"] is False
    with pytest.raises(APIError) as error:
        world.users["A"].client.table("series").update({"google_integration_id": foreign}).eq("id", world.sid).execute()
    assert error.value.code == "23503"


def test_reextraction_is_additive_and_never_deletes_omitted_items(world: World) -> None:
    owner = world.users["A"].client
    arguments = {"p_occurrence_id": world.past, "p_input_at": datetime.now(UTC).isoformat(), "p_closures": []}
    for key in ("first", "second"):
        assert owner.rpc(
            "apply_extraction", {**arguments, "p_items": [{"kind": "open_issue", "body": key, "extraction_key": key}]}
        ).execute().data == {"created": 1, "closed": 0}
    before = owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data
    assert owner.rpc("apply_extraction", {**arguments, "p_items": []}).execute().data == {"created": 0, "closed": 0}
    assert owner.table("memory_items").select("*").eq("series_id", world.sid).order("id").execute().data == before
    for key in ("first", "second"):
        assert owner.table("memory_items").select("body").eq("series_id", world.sid).eq(
            "extraction_key", key
        ).execute().data == [{"body": key}]


def test_topic_author_uses_calendar_name_then_verified_email_and_blocks_forgery(
    world: World, service_client: Client
) -> None:
    from pydantic import TypeAdapter

    member = world.users["B"]
    verified_email = world.users["D"].email.lower()
    payload = {"series_id": world.sid, "occurrence_id": world.oid, "submitted_by": str(member.id), "title": "Topic"}
    denied(member.client.table("agenda_topics").insert({**payload, "author_label": "Forged author"}).execute)
    service_client.table("series_attendees").update({"display_name": "Trusted calendar name"}).eq(
        "series_id", world.sid
    ).eq("email", verified_email).execute()
    rows = member.client.table("agenda_topics").insert(payload).execute().data
    assert TypeAdapter(list[dict[str, JSON]]).validate_python(rows)[0]["author_label"] == "Trusted calendar name"
    assert member.email.lower() != verified_email
    service_client.table("series_attendees").update({"display_name": None}).eq("series_id", world.sid).eq(
        "email", verified_email
    ).execute()
    rows = member.client.table("agenda_topics").insert(payload).execute().data
    assert TypeAdapter(list[dict[str, JSON]]).validate_python(rows)[0]["author_label"] == verified_email
    rows = (
        world.users["A"]
        .client.table("agenda_topics")
        .insert(
            {
                **payload,
                "submitted_by": str(world.users["A"].id),
            }
        )
        .execute()
        .data
    )
    assert TypeAdapter(list[dict[str, JSON]]).validate_python(rows)[0]["author_label"] == "メンバー"


async def test_failed_join_refresh_is_throttled_by_last_attempt(world: World, service_client: Client) -> None:
    from unittest.mock import AsyncMock
    from uuid import UUID

    from src.domain.entities.series import SeriesError
    from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
    from src.infrastructure.external.series_credentials import CredentialUnavailableError, SeriesCredentials
    from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl

    old = datetime.now(UTC) - timedelta(minutes=3)
    service_client.table("series").update({"calendar_refresh_attempted_at": old.isoformat()}).eq(
        "id", world.sid
    ).execute()
    repository = SeriesRepositoryImpl(world.users["A"].client)
    before = await repository.get(UUID(world.sid))
    credentials = AsyncMock(spec=SeriesCredentials)
    credentials.google_for_series.side_effect = CredentialUnavailableError("not_connected")
    mirror = SeriesCalendarMirror(service_client, credentials)
    with pytest.raises(SeriesError) as error:
        await mirror.refresh_for_join(world.sid)
    assert error.value.status == 409
    await mirror.refresh_for_join(world.sid)
    credentials.google_for_series.assert_awaited_once()
    after = await repository.get(UUID(world.sid))
    assert before is not None and after is not None
    assert after.calendar_synced_at == before.calendar_synced_at
    assert after.calendar_refresh_attempted_at is not None and after.calendar_refresh_attempted_at > old


async def test_join_refresh_accepts_omitted_attendees_as_a_warning(world: World, service_client: Client) -> None:
    from unittest.mock import AsyncMock, MagicMock

    from pydantic import TypeAdapter

    from src.domain.entities.series import CalendarSnapshot
    from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
    from src.infrastructure.external.series_credentials import GoogleApis, SeriesCredentials

    service_client.table("series").update(
        {"calendar_refresh_attempted_at": (datetime.now(UTC) - timedelta(minutes=3)).isoformat()}
    ).eq("id", world.sid).execute()
    snapshot = TypeAdapter(CalendarSnapshot).validate_python(
        {
            **world.snapshot,
            "ical_uid": world.sid,
            "event_id": "event",
            "attendees_omitted": True,
        }
    )
    credentials, calendar = AsyncMock(spec=SeriesCredentials), AsyncMock()
    calendar.snapshot.return_value = snapshot
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    await SeriesCalendarMirror(service_client, credentials).refresh_for_join(world.sid)
    assert world.users["B"].client.table("series").select("calendar_sync_error").eq("id", world.sid).execute().data == [
        {"calendar_sync_error": "attendees_omitted"}
    ]
