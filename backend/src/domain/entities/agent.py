"""Agent entity for domain layer.

Pure Python entity without SQLAlchemy/Pydantic dependencies.
Following ADR-0001 clean architecture principles.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Agent:
    """MTGエージェントを表すエンティティ.

    Attributes:
        id: エージェントの一意識別子
        user_id: 所有ユーザーのID
        name: エージェント名（MTG名）
        description: エージェントの説明
        slack_channel_id: 紐付けられたSlackチャンネルID
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    description: str | None = None
    slack_channel_id: str | None = None
    updated_at: datetime | None = None
    transcript_count: int = 3
    slack_message_days: int = 7

    def update_slack_channel(self, channel_id: str | None) -> None:
        """Slackチャンネルを紐付け/解除する.

        Args:
            channel_id: 紐付けるSlackチャンネルID。Noneの場合は紐付けを解除。
        """
        self.slack_channel_id = channel_id
        self.updated_at = datetime.now()

    def update_info(self, name: str | None = None, description: str | None = None) -> None:
        """エージェント情報を更新する.

        Args:
            name: 新しいエージェント名。Noneの場合は変更しない。
            description: 新しい説明。Noneの場合は変更しない。
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()

    def update_reference_settings(
        self,
        transcript_count: int | None = None,
        slack_message_days: int | None = None,
    ) -> None:
        """参照設定を更新する.

        Args:
            transcript_count: トランスクリプト参照件数（0-10）
            slack_message_days: Slackメッセージ取得日数（1-30）

        Raises:
            ValueError: 範囲外の値が指定された場合
        """
        if transcript_count is not None:
            if not 0 <= transcript_count <= 10:
                raise ValueError("transcript_count must be between 0 and 10")
            self.transcript_count = transcript_count
        if slack_message_days is not None:
            if not 1 <= slack_message_days <= 30:
                raise ValueError("slack_message_days must be between 1 and 30")
            self.slack_message_days = slack_message_days
        self.updated_at = datetime.now()
