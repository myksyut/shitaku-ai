"""GoogleIntegration repository implementation using Supabase.

Infrastructure layer implementation of GoogleIntegrationRepository interface.
Following ADR-0001 clean architecture principles.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from src.domain.entities.google_integration import GoogleIntegration
from src.domain.repositories.google_integration_repository import (
    GoogleIntegrationRepository,
)


class GoogleIntegrationRepositoryImpl(GoogleIntegrationRepository):
    """Google連携リポジトリのSupabase実装."""

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス.
        """
        self._client = client

    async def create(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Google連携を作成する."""
        if self._client is None:
            return integration

        data = {
            "id": str(integration.id),
            "user_id": str(integration.user_id),
            "email": integration.email,
            "encrypted_refresh_token": integration.encrypted_refresh_token,
            "granted_scopes": integration.granted_scopes,
            "created_at": integration.created_at.isoformat(),
        }
        self._client.table("google_integrations").insert(data).execute()
        return integration

    async def get_by_id(self, integration_id: UUID, user_id: UUID) -> GoogleIntegration | None:
        """IDでGoogle連携を取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("google_integrations")
            .select("*")
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_by_email(
        self,
        user_id: UUID,
        email: str,
    ) -> GoogleIntegration | None:
        """メールアドレスでGoogle連携を取得する."""
        if self._client is None:
            return None

        result = (
            self._client.table("google_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("email", email)
            .maybe_single()
            .execute()
        )

        if result is None or not result.data:
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        return self._to_entity(data)

    async def get_all(self, user_id: UUID) -> list[GoogleIntegration]:
        """ユーザーの全Google連携を取得する."""
        if self._client is None:
            return []

        result = (
            self._client.table("google_integrations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return [self._to_entity(dict(row)) for row in result.data]  # type: ignore[arg-type]

    async def update(self, integration: GoogleIntegration) -> GoogleIntegration:
        """Google連携を更新する."""
        if self._client is None:
            return integration

        data = {
            "email": integration.email,
            "encrypted_refresh_token": integration.encrypted_refresh_token,
            "granted_scopes": integration.granted_scopes,
            "updated_at": datetime.now().isoformat(),
        }
        (
            self._client.table("google_integrations")
            .update(data)
            .eq("id", str(integration.id))
            .eq("user_id", str(integration.user_id))
            .execute()
        )
        return integration

    async def delete(self, integration_id: UUID, user_id: UUID) -> bool:
        """Google連携を削除する."""
        if self._client is None:
            return False

        result = (
            self._client.table("google_integrations")
            .delete()
            .eq("id", str(integration_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    def _to_entity(self, data: dict[str, Any]) -> GoogleIntegration:
        """DB結果をGoogleIntegrationエンティティに変換する."""
        created_at_str = data["created_at"]
        updated_at_str = data.get("updated_at")
        granted_scopes_raw = data.get("granted_scopes", [])

        # granted_scopesがNoneの場合は空リストにする
        granted_scopes: list[str] = list(granted_scopes_raw) if granted_scopes_raw is not None else []

        return GoogleIntegration(
            id=UUID(str(data["id"])),
            user_id=UUID(str(data["user_id"])),
            email=str(data["email"]),
            encrypted_refresh_token=str(data["encrypted_refresh_token"]),
            granted_scopes=granted_scopes,
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(str(updated_at_str))
                if updated_at_str and isinstance(updated_at_str, str)
                else None
            ),
        )
