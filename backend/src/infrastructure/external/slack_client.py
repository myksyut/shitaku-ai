"""Slack Web API client using slack-sdk.

Provides methods for interacting with Slack workspace data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


@dataclass
class SlackChannel:
    """Slackチャンネル情報."""

    id: str
    name: str


@dataclass
class SlackMessageData:
    """Slackメッセージ情報."""

    ts: str
    user_name: str
    text: str
    posted_at: datetime


class SlackClient:
    """Slack Web APIクライアント.

    Attributes:
        client: slack-sdk WebClient instance.
    """

    def __init__(self, access_token: str) -> None:
        """SlackClientを初期化する.

        Args:
            access_token: Slack OAuth access token.
        """
        self.client = WebClient(token=access_token)

    def get_channels(self) -> list[SlackChannel]:
        """チャンネル一覧を取得する.

        Returns:
            List of SlackChannel objects.

        Raises:
            SlackApiError: If API call fails.
        """
        try:
            result = self.client.conversations_list(
                types="public_channel,private_channel"
            )
            channels: list[dict[str, str]] = result.get("channels", [])
            return [
                SlackChannel(id=c["id"], name=c["name"])
                for c in channels
            ]
        except SlackApiError as e:
            logger.error("Failed to get channels: %s", e)
            raise

    def get_messages(
        self,
        channel_id: str,
        oldest: datetime,
        latest: datetime | None = None,
    ) -> list[SlackMessageData]:
        """期間指定でメッセージを取得する.

        Args:
            channel_id: Slack channel ID.
            oldest: Start of time range (inclusive).
            latest: End of time range. None means now.

        Returns:
            List of SlackMessageData objects.

        Raises:
            SlackApiError: If API call fails.
        """
        try:
            params: dict[str, str | int] = {
                "channel": channel_id,
                "oldest": str(oldest.timestamp()),
                "limit": 1000,
            }
            if latest:
                params["latest"] = str(latest.timestamp())

            result = self.client.conversations_history(**params)  # type: ignore[arg-type]

            messages: list[SlackMessageData] = []
            raw_messages: list[dict[str, str]] = result.get("messages", [])

            for msg in raw_messages:
                # Skip system messages (channel_join, etc.)
                if msg.get("type") == "message" and "subtype" not in msg:
                    user_name = self._get_user_name(msg.get("user", "unknown"))
                    ts = msg["ts"]
                    messages.append(
                        SlackMessageData(
                            ts=ts,
                            user_name=user_name,
                            text=msg.get("text", ""),
                            posted_at=datetime.fromtimestamp(float(ts)),
                        )
                    )

            return messages

        except SlackApiError as e:
            logger.error("Failed to get messages: %s", e)
            raise

    def _get_user_name(self, user_id: str) -> str:
        """ユーザーIDから表示名を取得する.

        Args:
            user_id: Slack user ID.

        Returns:
            User's display name, or user_id if lookup fails.
        """
        try:
            result = self.client.users_info(user=user_id)
            user: dict[str, str] = result.get("user", {})
            return user.get("real_name") or user.get("name", user_id)
        except SlackApiError:
            return user_id

    def verify_token(self) -> bool:
        """トークンの有効性を確認する.

        Returns:
            True if token is valid, False otherwise.
        """
        try:
            self.client.auth_test()
            return True
        except SlackApiError:
            return False
