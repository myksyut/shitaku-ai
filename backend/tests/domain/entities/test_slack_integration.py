"""SlackIntegration and SlackMessage entity tests."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.slack_integration import SlackIntegration, SlackMessage


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


class TestSlackMessage:
    """SlackMessageエンティティのテスト"""

    def test_create_slack_message(self) -> None:
        """SlackMessageが正しくインスタンス化できる"""
        message_id = uuid4()
        integration_id = uuid4()
        posted_at = datetime.now()

        message = SlackMessage(
            id=message_id,
            integration_id=integration_id,
            channel_id="C01234567",
            message_ts="1234567890.123456",
            user_name="田中太郎",
            text="本日のMTGは15時からです",
            posted_at=posted_at,
        )

        assert message.id == message_id
        assert message.integration_id == integration_id
        assert message.channel_id == "C01234567"
        assert message.message_ts == "1234567890.123456"
        assert message.user_name == "田中太郎"
        assert message.text == "本日のMTGは15時からです"
        assert message.posted_at == posted_at

    def test_to_display_text(self) -> None:
        """to_display_textで表示用テキストが生成される"""
        message = SlackMessage(
            id=uuid4(),
            integration_id=uuid4(),
            channel_id="C01234567",
            message_ts="1234567890.123456",
            user_name="田中太郎",
            text="本日のMTGは15時からです",
            posted_at=datetime(2025, 1, 15, 14, 30),
        )

        display_text = message.to_display_text()

        assert display_text == "[2025-01-15 14:30] 田中太郎: 本日のMTGは15時からです"

    def test_slack_message_equality(self) -> None:
        """同じ値を持つSlackMessageは等しい"""
        message_id = uuid4()
        integration_id = uuid4()
        posted_at = datetime.now()

        message1 = SlackMessage(
            id=message_id,
            integration_id=integration_id,
            channel_id="C01234567",
            message_ts="1234567890.123456",
            user_name="テスト",
            text="テストメッセージ",
            posted_at=posted_at,
        )
        message2 = SlackMessage(
            id=message_id,
            integration_id=integration_id,
            channel_id="C01234567",
            message_ts="1234567890.123456",
            user_name="テスト",
            text="テストメッセージ",
            posted_at=posted_at,
        )

        assert message1 == message2
