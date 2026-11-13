from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.slack_integration import SlackIntegration
from src.domain.repositories.slack_integration_repository import SlackIntegrationRepository


class SlackIntegrationRepositoryImpl(SlackIntegrationRepository):
    """Supabase persistence with explicit credential-owner filters."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, integration: SlackIntegration) -> SlackIntegration:
        """Create the owner's integration."""
        self._client.table("slack_integrations").insert(
            TypeAdapter(SlackIntegration).dump_python(integration, mode="json")
        ).execute()
        return integration

    def get_by_id(self, integration_id: UUID, user_id: UUID) -> SlackIntegration | None:
        """Read only the selected owner's binding."""
        rows = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[SlackIntegration]).validate_python(rows)
        return items[0] if items else None

    def get_by_workspace(self, user_id: UUID, workspace_id: str) -> SlackIntegration | None:
        """Find a workspace under its authenticated owner."""
        rows = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("user_id", str(user_id))
            .execute()
            .data
        )
        items = TypeAdapter(list[SlackIntegration]).validate_python(rows)
        return items[0] if items else None

    def get_all(self, user_id: UUID) -> list[SlackIntegration]:
        """List personal workspace bindings."""
        rows = (
            self._client.table("slack_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
            .data
        )
        return TypeAdapter(list[SlackIntegration]).validate_python(rows)

    def update(self, integration: SlackIntegration) -> SlackIntegration:
        """Update credentials only within their owner's row."""
        self._client.table("slack_integrations").update(
            {
                "encrypted_access_token": integration.encrypted_access_token,
                "workspace_name": integration.workspace_name,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(integration.id)).eq("user_id", str(integration.user_id)).execute()
        return integration

    def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Delete the user's Slack integration."""
        return bool(
            self._client.table("slack_integrations")
            .delete()
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .execute()
            .data
        )
