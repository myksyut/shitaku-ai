from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter
from supabase import Client

from src.domain.entities.google_integration import GoogleIntegration
from src.domain.repositories.google_integration_repository import GoogleIntegrationRepository


class GoogleIntegrationRepositoryImpl(GoogleIntegrationRepository):
    """Personal Google credentials with explicit integration-owner predicates."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Persist an owned credential binding."""
        self._client.table("google_integrations").insert(
            TypeAdapter(GoogleIntegration).dump_python(integration, mode="json")
        ).execute()
        return integration

    def get_by_id(self, integration_id: UUID, user_id: UUID) -> GoogleIntegration | None:
        """Read only the explicitly selected owner's integration."""
        result = (
            self._client.table("google_integrations")
            .select("*")
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        return self._to_entity(result.data) if result is not None and result.data else None

    def get_by_email(self, user_id: UUID, email: str) -> GoogleIntegration | None:
        """Find a user's Google integration by email."""
        result = (
            self._client.table("google_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return self._to_entity(result.data) if result is not None and result.data else None

    def get_all(self, user_id: UUID) -> list[GoogleIntegration]:
        """List the user's Google integrations."""
        rows = (
            self._client.table("google_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
            .data
        )
        return [self._to_entity(row) for row in rows]

    def update(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Update only the checked owner's credential row."""
        self._client.table("google_integrations").update(
            {
                "email": integration.email,
                "encrypted_refresh_token": integration.encrypted_refresh_token,
                "granted_scopes": integration.granted_scopes,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(integration.id)).eq("user_id", str(integration.user_id)).execute()
        return integration

    def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Delete the user's Google integration."""
        return bool(
            self._client.table("google_integrations")
            .delete()
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .execute()
            .data
        )

    def _to_entity(self, data: object) -> GoogleIntegration:
        row = TypeAdapter(dict[str, object]).validate_python(data)
        return TypeAdapter(GoogleIntegration).validate_python(
            {**row, "granted_scopes": row.get("granted_scopes") or []}
        )
