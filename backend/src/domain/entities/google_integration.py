"""GoogleIntegration entity for domain layer.

Pure Python entity without external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class GoogleIntegration:
    """Google連携を表すエンティティ.

    Attributes:
        id: Unique identifier for the integration.
        user_id: ID of the owning user.
        email: Google account email address.
        encrypted_refresh_token: Fernet encrypted OAuth refresh token.
        granted_scopes: List of OAuth scopes granted by the user.
        created_at: Timestamp when the integration was created.
        updated_at: Timestamp when the integration was last updated.
    """

    id: UUID
    user_id: UUID
    email: str
    encrypted_refresh_token: str
    granted_scopes: list[str]
    created_at: datetime
    updated_at: datetime | None

    def has_scope(self, scope: str) -> bool:
        """指定スコープが許可済みか確認.

        Args:
            scope: OAuth scope to check.

        Returns:
            True if the scope is granted, False otherwise.
        """
        return scope in self.granted_scopes

    def add_scopes(self, new_scopes: list[str]) -> None:
        """スコープを追加（Incremental Authorization用）.

        重複するスコープは追加されない。

        Args:
            new_scopes: List of new scopes to add.
        """
        if not new_scopes:
            return

        for scope in new_scopes:
            if scope not in self.granted_scopes:
                self.granted_scopes.append(scope)

        self.updated_at = datetime.now()

    def update_token(self, encrypted_token: str) -> None:
        """リフレッシュトークンを更新.

        Args:
            encrypted_token: New encrypted refresh token.
        """
        self.encrypted_refresh_token = encrypted_token
        self.updated_at = datetime.now()
