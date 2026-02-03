"""Slack Web API client using slack-sdk.

Provides methods for interacting with Slack workspace data.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# チャンネルキャッシュのTTL（秒）
CHANNEL_CACHE_TTL_SECONDS = 300  # 5分


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
    thread_ts: str | None = None
    reply_count: int = 0


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
        self._user_cache: dict[str, str] = {}
        self._channel_cache: list[SlackChannel] | None = None
        self._channel_cache_timestamp: float | None = None

    def get_channels(self) -> list[SlackChannel]:
        """チャンネル一覧を取得する（ページネーション対応、TTLキャッシュ付き）.

        Returns:
            List of SlackChannel objects.

        Raises:
            SlackApiError: If API call fails.
        """
        # キャッシュヒット判定
        if self._channel_cache is not None and self._channel_cache_timestamp is not None:
            elapsed = time.time() - self._channel_cache_timestamp
            if elapsed < CHANNEL_CACHE_TTL_SECONDS:
                logger.debug("Channel cache hit (age: %.1fs)", elapsed)
                return self._channel_cache

        # キャッシュミス → API呼び出し
        try:
            all_channels: list[SlackChannel] = []
            cursor: str | None = None

            while True:
                result = self.client.conversations_list(
                    types="public_channel,private_channel",
                    limit=200,
                    cursor=cursor,
                )
                channels: list[dict[str, str]] = result.get("channels", [])
                all_channels.extend(SlackChannel(id=c["id"], name=c["name"]) for c in channels)

                # 次ページのcursorを取得
                response_metadata: dict[str, str] = result.get("response_metadata", {})
                cursor = response_metadata.get("next_cursor")
                if not cursor:
                    break

            # キャッシュを更新
            self._channel_cache = all_channels
            self._channel_cache_timestamp = time.time()
            logger.debug("Channel cache updated (%d channels)", len(all_channels))

            return all_channels
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
                            thread_ts=msg.get("thread_ts"),
                            reply_count=int(msg.get("reply_count", 0)),
                        )
                    )

            return messages

        except SlackApiError as e:
            logger.error("Failed to get messages: %s", e)
            raise

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> list[SlackMessageData]:
        """スレッドの返信メッセージを取得する.

        Args:
            channel_id: Slack channel ID.
            thread_ts: Parent message timestamp (thread root).

        Returns:
            List of SlackMessageData objects (replies only, excludes parent).

        Raises:
            SlackApiError: If API call fails.
        """
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000,
            )

            messages: list[SlackMessageData] = []
            raw_messages: list[dict[str, str]] = result.get("messages", [])

            for msg in raw_messages:
                # Skip the parent message (first message in thread)
                if msg.get("ts") == thread_ts:
                    continue

                if msg.get("type") == "message" and "subtype" not in msg:
                    user_name = self._get_user_name(msg.get("user", "unknown"))
                    ts = msg["ts"]
                    messages.append(
                        SlackMessageData(
                            ts=ts,
                            user_name=user_name,
                            text=msg.get("text", ""),
                            posted_at=datetime.fromtimestamp(float(ts)),
                            thread_ts=msg.get("thread_ts"),
                            reply_count=0,
                        )
                    )

            return messages

        except SlackApiError as e:
            logger.error("Failed to get thread replies: %s", e)
            raise

    def _get_user_name(self, user_id: str) -> str:
        """ユーザーIDから表示名を取得する.

        Args:
            user_id: Slack user ID.

        Returns:
            User's display name, or user_id if lookup fails.
        """
        # キャッシュヒット
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        # キャッシュミス → API呼び出し
        try:
            result = self.client.users_info(user=user_id)
            user: dict[str, str] = result.get("user", {})
            name = user.get("real_name") or user.get("name", user_id)
            self._user_cache[user_id] = name
            return name
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
