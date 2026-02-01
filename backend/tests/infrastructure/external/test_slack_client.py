"""SlackClient tests with mocked Slack API."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from src.infrastructure.external.slack_client import (
    SlackChannel,
    SlackClient,
    SlackMessageData,
)


class TestSlackClient:
    """SlackClientのテスト"""

    @pytest.fixture
    def mock_web_client(self) -> MagicMock:
        """モック化されたWebClientを返す"""
        return MagicMock()

    @pytest.fixture
    def slack_client(self, mock_web_client: MagicMock) -> SlackClient:
        """SlackClientインスタンスを返す"""
        with patch("src.infrastructure.external.slack_client.WebClient", return_value=mock_web_client):
            return SlackClient("xoxb-test-token")

    def test_get_channels_success(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """チャンネル一覧を正しく取得できる"""
        mock_web_client.conversations_list.return_value = {
            "ok": True,
            "channels": [
                {"id": "C001", "name": "general"},
                {"id": "C002", "name": "random"},
            ],
        }

        channels = slack_client.get_channels()

        assert len(channels) == 2
        assert channels[0] == SlackChannel(id="C001", name="general")
        assert channels[1] == SlackChannel(id="C002", name="random")
        mock_web_client.conversations_list.assert_called_once_with(
            types="public_channel,private_channel"
        )

    def test_get_channels_api_error(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """API エラー時に例外を発生させる"""
        mock_web_client.conversations_list.side_effect = SlackApiError(  # type: ignore[no-untyped-call]
            message="invalid_auth",
            response={"ok": False, "error": "invalid_auth"},
        )

        with pytest.raises(SlackApiError):
            slack_client.get_channels()

    def test_get_messages_success(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """メッセージを正しく取得できる"""
        mock_web_client.conversations_history.return_value = {
            "ok": True,
            "messages": [
                {"type": "message", "ts": "1704067200.000001", "user": "U001", "text": "Hello"},
                {"type": "message", "ts": "1704067201.000002", "user": "U002", "text": "World"},
                # subtypeがあるメッセージは除外される
                {"type": "message", "subtype": "channel_join", "ts": "1704067202.000003", "user": "U003"},
            ],
        }
        mock_web_client.users_info.side_effect = [
            {"ok": True, "user": {"real_name": "田中太郎", "name": "tanaka"}},
            {"ok": True, "user": {"real_name": "山田花子", "name": "yamada"}},
        ]

        oldest = datetime(2024, 1, 1, 0, 0, 0)
        messages = slack_client.get_messages("C001", oldest)

        assert len(messages) == 2
        assert messages[0].text == "Hello"
        assert messages[0].user_name == "田中太郎"
        assert messages[1].text == "World"
        assert messages[1].user_name == "山田花子"

    def test_get_messages_with_latest(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """latest指定でメッセージを取得できる"""
        mock_web_client.conversations_history.return_value = {
            "ok": True,
            "messages": [],
        }

        oldest = datetime(2024, 1, 1, 0, 0, 0)
        latest = datetime(2024, 1, 31, 23, 59, 59)
        slack_client.get_messages("C001", oldest, latest)

        call_kwargs = mock_web_client.conversations_history.call_args[1]
        assert "latest" in call_kwargs

    def test_verify_token_success(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """トークン検証が成功する"""
        mock_web_client.auth_test.return_value = {"ok": True}

        assert slack_client.verify_token() is True

    def test_verify_token_failure(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """トークン検証が失敗する"""
        mock_web_client.auth_test.side_effect = SlackApiError(  # type: ignore[no-untyped-call]
            message="invalid_auth",
            response={"ok": False, "error": "invalid_auth"},
        )

        assert slack_client.verify_token() is False

    def test_get_user_name_fallback(self, slack_client: SlackClient, mock_web_client: MagicMock) -> None:
        """ユーザー情報取得失敗時はuser_idを返す"""
        mock_web_client.conversations_history.return_value = {
            "ok": True,
            "messages": [
                {"type": "message", "ts": "1704067200.000001", "user": "U001", "text": "Hello"},
            ],
        }
        mock_web_client.users_info.side_effect = SlackApiError(  # type: ignore[no-untyped-call]
            message="user_not_found",
            response={"ok": False, "error": "user_not_found"},
        )

        oldest = datetime(2024, 1, 1, 0, 0, 0)
        messages = slack_client.get_messages("C001", oldest)

        assert messages[0].user_name == "U001"


class TestSlackDataClasses:
    """データクラスのテスト"""

    def test_slack_channel_creation(self) -> None:
        """SlackChannelが正しく作成できる"""
        channel = SlackChannel(id="C001", name="general")
        assert channel.id == "C001"
        assert channel.name == "general"

    def test_slack_message_data_creation(self) -> None:
        """SlackMessageDataが正しく作成できる"""
        posted_at = datetime(2024, 1, 1, 12, 0, 0)
        message = SlackMessageData(
            ts="1704067200.000001",
            user_name="田中太郎",
            text="テストメッセージ",
            posted_at=posted_at,
        )
        assert message.ts == "1704067200.000001"
        assert message.user_name == "田中太郎"
        assert message.text == "テストメッセージ"
        assert message.posted_at == posted_at
