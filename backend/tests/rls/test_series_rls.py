from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError
from postgrest.types import JSON
from supabase import Client

from tests.rls.conftest import RlsUser


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
    add_identity(users["B"], users["B"].email.upper(), True, "google")
    add_identity(users["E"], users["E"].email, False, "google")
    # The email-provider account claims the attendee's address, without a Google identity.
    add_identity(users["D"], users["B"].email, True, "email")
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
            {"email": users[tag].email, "display_name": tag, "is_organizer": tag == "A"} for tag in ("A", "B", "E")
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
    assert overview == [
        {"extracted_at": input_at.isoformat(), "latest_knowledge_at": (input_at + timedelta(seconds=1)).isoformat()}
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
