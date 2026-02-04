"""OAuthStateRepository interface for domain layer.

Protocol class defining the contract for OAuth state persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from typing import Protocol

from src.domain.entities.oauth_state import OAuthState


class OAuthStateRepository(Protocol):
    """OAuth stateリポジトリのインターフェース.

    OAuth認証stateの永続化操作を定義する。
    実装はインフラストラクチャ層で提供される。
    """

    async def create(self, oauth_state: OAuthState) -> OAuthState:
        """OAuth stateを作成する.

        Args:
            oauth_state: 作成するOAuthStateエンティティ.

        Returns:
            作成されたOAuthStateエンティティ.
        """
        ...

    async def get_and_delete(self, state: str) -> OAuthState | None:
        """stateを取得し、同時に削除する.

        アトミック操作として実装される。
        stateが存在しない場合はNoneを返す。

        Args:
            state: 検索するstateトークン.

        Returns:
            OAuthStateエンティティ、または存在しない場合はNone.
        """
        ...

    async def cleanup_expired(self) -> int:
        """期限切れのstateを削除する.

        Returns:
            削除されたレコード数.
        """
        ...
