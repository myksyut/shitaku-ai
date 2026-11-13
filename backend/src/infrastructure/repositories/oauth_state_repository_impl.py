"""OAuthState repository implementation using Supabase.

Infrastructure layer implementation of OAuthStateRepository interface.
Following ADR-0004 RLS-based authorization architecture.
"""

import logging
from datetime import datetime

from postgrest.types import JSON
from pydantic import TypeAdapter

from src.domain.entities.oauth_state import OAuthState
from src.infrastructure.external.supabase_client import ServiceClient, UserClient

logger = logging.getLogger(__name__)


class OAuthStateRepositoryImpl:
    """OAuth stateリポジトリのSupabase実装.

    ADR-0004のRLSパターンに準拠:
    - OAuth開始時: get_user_supabase_client()（ユーザーコンテキスト付き）
    - Callback時: service_role（RLSバイパス）
    """

    def __init__(self, client: UserClient | ServiceClient) -> None:
        """リポジトリを初期化する.

        Args:
            client: Supabaseクライアントインスタンス.
        """
        self._client = client

    def create(self, oauth_state: OAuthState) -> OAuthState:
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

        data: dict[str, JSON] = {
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

    def get_and_delete(self, state: str) -> OAuthState | None:
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

        data = TypeAdapter(dict[str, object]).validate_python(result.data)
        oauth_state = self._to_entity(data)

        # 取得後に削除（一回使用のため）
        self._client.table("oauth_states").delete().eq("state", state).execute()

        logger.info("Validated OAuth state: provider=%s", oauth_state.provider)
        return oauth_state

    def cleanup_expired(self) -> int:
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

    def _to_entity(self, data: object) -> OAuthState:
        return TypeAdapter(OAuthState).validate_python(data)
