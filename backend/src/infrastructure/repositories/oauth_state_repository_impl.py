"""OAuthState repository implementation using Supabase.

Infrastructure layer implementation of OAuthStateRepository interface.
Following ADR-0004 RLS-based authorization architecture.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from src.domain.entities.oauth_state import OAuthState

logger = logging.getLogger(__name__)


class OAuthStateRepositoryImpl:
    """OAuth stateリポジトリのSupabase実装.

    ADR-0004のRLSパターンに準拠:
    - OAuth開始時: get_user_supabase_client()（ユーザーコンテキスト付き）
    - Callback時: get_supabase_client()（service_role、RLSバイパス）
    """

    def __init__(self, client: Client) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス.
        """
        self._client = client

    async def create(self, oauth_state: OAuthState) -> OAuthState:
        """OAuth stateを作成する.

        Args:
            oauth_state: 作成するOAuthStateエンティティ.

        Returns:
            作成されたOAuthStateエンティティ.
        """
        logger.info(
            "Creating OAuth state: provider=%s, user_id=%s",
            oauth_state.provider,
            oauth_state.user_id,
        )

        data: dict[str, Any] = {
            "id": str(oauth_state.id),
            "state": oauth_state.state,
            "user_id": str(oauth_state.user_id),
            "provider": oauth_state.provider,
            "scopes": oauth_state.scopes,
            "redirect_origin": oauth_state.redirect_origin,
            "expires_at": oauth_state.expires_at.isoformat(),
            "created_at": oauth_state.created_at.isoformat(),
        }

        self._client.table("oauth_states").insert(data).execute()
        return oauth_state

    async def get_and_delete(self, state: str) -> OAuthState | None:
        """stateを取得し、同時に削除する（アトミック操作）.

        callback時にservice_roleクライアントで呼び出されることを想定。
        RLSをバイパスして任意のstateにアクセス可能。

        Args:
            state: 検索するstateトークン.

        Returns:
            OAuthStateエンティティ、または存在しない場合はNone.
        """
        # まずstateを取得
        result = self._client.table("oauth_states").select("*").eq("state", state).maybe_single().execute()

        if result is None or not result.data:
            logger.warning("Invalid OAuth state: state=%s...", state[:8] if state else "")
            return None

        data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
        oauth_state = self._to_entity(data)

        # 取得後に削除（一回使用のため）
        self._client.table("oauth_states").delete().eq("state", state).execute()

        logger.info("Validated OAuth state: provider=%s", oauth_state.provider)
        return oauth_state

    async def cleanup_expired(self) -> int:
        """期限切れのstateを全て削除する.

        Returns:
            削除されたレコード数.
        """
        now = datetime.now().isoformat()

        result = self._client.table("oauth_states").delete().lt("expires_at", now).execute()

        deleted_count = len(result.data) if result.data else 0
        if deleted_count > 0:
            logger.info("Cleaned up %d expired OAuth states", deleted_count)

        return deleted_count

    def _to_entity(self, data: dict[str, Any]) -> OAuthState:
        """DB結果をOAuthStateエンティティに変換する.

        Args:
            data: Database row as dictionary.

        Returns:
            OAuthState entity.
        """
        expires_at_str = data["expires_at"]
        created_at_str = data["created_at"]
        scopes_raw = data.get("scopes")

        # scopesの型変換: DBからはlist | Noneが返る
        scopes: list[str] | None = [str(s) for s in scopes_raw] if isinstance(scopes_raw, list) else None

        redirect_origin_raw = data.get("redirect_origin")
        redirect_origin: str | None = str(redirect_origin_raw) if redirect_origin_raw is not None else None

        return OAuthState(
            id=UUID(str(data["id"])),
            state=str(data["state"]),
            user_id=UUID(str(data["user_id"])),
            provider=str(data["provider"]),
            scopes=scopes,
            redirect_origin=redirect_origin,
            expires_at=(
                datetime.fromisoformat(str(expires_at_str)) if isinstance(expires_at_str, str) else datetime.now()
            ),
            created_at=(
                datetime.fromisoformat(str(created_at_str)) if isinstance(created_at_str, str) else datetime.now()
            ),
        )
