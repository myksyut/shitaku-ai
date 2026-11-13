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
    topic_id = str(uuid4())
    topic = (
        member.client.table("agenda_topics")
        .insert(
            {
                "id": topic_id,
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
        == []
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
def bedrock_stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
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
                        "input": {
                            "new_items": [{"kind": "decision", "body": "Extracted through real HTTP"}],
                            "closures": [],
                        },
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
