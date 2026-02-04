"""OAuthState entity for domain layer.

Pure Python entity without external dependencies.
Used for CSRF protection in OAuth 2.0 flows.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class OAuthState:
    """OAuth認証stateエンティティ.

    OAuth 2.0認証フローにおけるCSRF対策用stateを表現する。
    stateはユーザーID、プロバイダー、有効期限と紐付けて管理される。

    Attributes:
        id: Unique identifier for the state record.
        state: CSRF protection token (URL-safe random string).
        user_id: ID of the user initiating OAuth flow.
        provider: OAuth provider name ('slack' | 'google').
        scopes: Optional list of requested OAuth scopes.
        expires_at: Timestamp when the state expires.
        created_at: Timestamp when the state was created.
    """

    id: UUID
    state: str
    user_id: UUID
    provider: str  # 'slack' | 'google'
    scopes: list[str] | None
    expires_at: datetime
    created_at: datetime

    def is_expired(self) -> bool:
        """有効期限が切れているか確認する.

        Returns:
            True if expired, False otherwise.
        """
        now = datetime.now(UTC)
        # expires_atがnaiveの場合はUTC想定で比較
        if self.expires_at.tzinfo is None:
            return now.replace(tzinfo=None) > self.expires_at
        return now > self.expires_at
