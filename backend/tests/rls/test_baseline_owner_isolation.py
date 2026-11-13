from dataclasses import dataclass
from uuid import uuid4

import pytest

from src.infrastructure.external.supabase_client import ServiceClient
from tests.rls.conftest import RlsUser


@dataclass(frozen=True)
class OwnedRow:
    table: str
    id: str
    column: str


@pytest.fixture(params=("google_integrations", "slack_integrations", "oauth_states"))
def owned_row(request: pytest.FixtureRequest, service_client: ServiceClient, creator: RlsUser) -> OwnedRow:
    row_id = str(uuid4())
    if request.param == "google_integrations":
        service_client.table("google_integrations").insert(
            {"id": row_id, "user_id": str(creator.id), "email": creator.email, "encrypted_refresh_token": "secret"}
        ).execute()
        column = "email"
    elif request.param == "slack_integrations":
        service_client.table("slack_integrations").insert(
            {
                "id": row_id,
                "user_id": str(creator.id),
                "workspace_id": row_id,
                "workspace_name": "Private",
                "encrypted_access_token": "secret",
            }
        ).execute()
        column = "workspace_name"
    else:
        service_client.table("oauth_states").insert(
            {"id": row_id, "user_id": str(creator.id), "provider": "google", "state": row_id}
        ).execute()
        column = "state"
    return OwnedRow(str(request.param), row_id, column)


def test_owner_reads_personal_credentials(owned_row: OwnedRow, creator: RlsUser) -> None:
    assert creator.client.table(owned_row.table).select("id").eq("id", owned_row.id).execute().data == [
        {"id": owned_row.id}
    ]


def test_outsider_cannot_read_update_delete(owned_row: OwnedRow, outsider: RlsUser, creator: RlsUser) -> None:
    assert outsider.client.table(owned_row.table).select("id").eq("id", owned_row.id).execute().data == []
    assert (
        outsider.client.table(owned_row.table)
        .update({owned_row.column: "forged"})
        .eq("id", owned_row.id)
        .execute()
        .data
        == []
    )
    assert outsider.client.table(owned_row.table).delete().eq("id", owned_row.id).execute().data == []
    assert creator.client.table(owned_row.table).select("id").eq("id", owned_row.id).execute().data == [
        {"id": owned_row.id}
    ]
