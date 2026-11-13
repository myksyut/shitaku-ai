from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from supabase import Client

if TYPE_CHECKING:
    from tests.rls.conftest import RlsUser


@dataclass(frozen=True)
class OwnedRow:
    table: str
    id: UUID
    column: str
    value: str


@pytest.fixture(params=("agents", "knowledge"))
def owned_row(request: pytest.FixtureRequest, service_client: Client, creator: RlsUser) -> OwnedRow:
    agent_id = uuid4()
    agent_name = "Owner's agent"
    service_client.table("agents").insert(
        {"id": str(agent_id), "user_id": str(creator.id), "name": agent_name}
    ).execute()
    if request.param == "agents":
        return OwnedRow(table="agents", id=agent_id, column="name", value=agent_name)

    knowledge_id = uuid4()
    normalized_text = "Owner's knowledge"
    service_client.table("knowledge").insert(
        {
            "id": str(knowledge_id),
            "agent_id": str(agent_id),
            "user_id": str(creator.id),
            "original_text": "Original meeting notes",
            "normalized_text": normalized_text,
            "meeting_date": "2026-01-01T00:00:00+00:00",
        }
    ).execute()
    return OwnedRow(table="knowledge", id=knowledge_id, column="normalized_text", value=normalized_text)


def test_owner_can_read_own_row(owned_row: OwnedRow, creator: RlsUser) -> None:
    response = creator.client.table(owned_row.table).select("id,user_id").eq("id", str(owned_row.id)).execute()

    assert response.data == [{"id": str(owned_row.id), "user_id": str(creator.id)}], (
        f"The owner must be able to read their own {owned_row.table} row"
    )


def test_another_user_cannot_read_owner_row(owned_row: OwnedRow, attendee: RlsUser) -> None:
    response = attendee.client.table(owned_row.table).select("id").eq("id", str(owned_row.id)).execute()

    assert response.data == [], f"RLS must hide another user's {owned_row.table} row without an application user filter"


def test_another_user_cannot_update_owner_row(owned_row: OwnedRow, creator: RlsUser, outsider: RlsUser) -> None:
    response = (
        outsider.client.table(owned_row.table)
        .update({owned_row.column: "Unauthorized change"})
        .eq("id", str(owned_row.id))
        .execute()
    )

    assert response.data == [], f"Updating another user's {owned_row.table} row must affect zero rows"
    remaining = (
        creator.client.table(owned_row.table).select(f"id,{owned_row.column}").eq("id", str(owned_row.id)).execute()
    )
    assert remaining.data == [{"id": str(owned_row.id), owned_row.column: owned_row.value}], (
        f"An unauthorized update must leave the owner's {owned_row.table} content unchanged"
    )


def test_another_user_cannot_delete_owner_row(owned_row: OwnedRow, creator: RlsUser, outsider: RlsUser) -> None:
    response = outsider.client.table(owned_row.table).delete().eq("id", str(owned_row.id)).execute()

    assert response.data == [], f"Deleting another user's {owned_row.table} row must affect zero rows"
    remaining = creator.client.table(owned_row.table).select("id").eq("id", str(owned_row.id)).execute()
    assert remaining.data == [{"id": str(owned_row.id)}], (
        f"An unauthorized delete must leave the owner's {owned_row.table} row intact"
    )
