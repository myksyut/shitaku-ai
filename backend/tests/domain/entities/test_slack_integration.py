"""SlackIntegration entity tests."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.slack_integration import SlackIntegration


class TestSlackIntegration:
    """SlackIntegrationエンティティのテスト"""

    def test_create_slack_integration(self) -> None:
        """SlackIntegrationが正しくインスタンス化できる"""
        integration_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        integration = SlackIntegration(
            id=integration_id,
            user_id=user_id,
            workspace_id="T01234567",
            workspace_name="テストワークスペース",
            encrypted_access_token="encrypted_token_here",
            created_at=now,
            updated_at=None,
        )

        assert integration.id == integration_id
        assert integration.user_id == user_id
        assert integration.workspace_id == "T01234567"
        assert integration.workspace_name == "テストワークスペース"
        assert integration.encrypted_access_token == "encrypted_token_here"
        assert integration.created_at == now
        assert integration.updated_at is None

    def test_update_token(self) -> None:
        """update_tokenでトークンが更新される"""
        integration = SlackIntegration(
            id=uuid4(),
            user_id=uuid4(),
            workspace_id="T01234567",
            workspace_name="テストワークスペース",
            encrypted_access_token="old_token",
            created_at=datetime.now(),
            updated_at=None,
        )

        integration.update_token("new_encrypted_token")

        assert integration.encrypted_access_token == "new_encrypted_token"
        assert integration.updated_at is not None

    def test_slack_integration_equality(self) -> None:
        """同じ値を持つSlackIntegrationは等しい"""
        integration_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        integration1 = SlackIntegration(
            id=integration_id,
            user_id=user_id,
            workspace_id="T01234567",
            workspace_name="テスト",
            encrypted_access_token="token",
            created_at=now,
            updated_at=None,
        )
        integration2 = SlackIntegration(
            id=integration_id,
            user_id=user_id,
            workspace_id="T01234567",
            workspace_name="テスト",
            encrypted_access_token="token",
            created_at=now,
            updated_at=None,
        )

        assert integration1 == integration2
