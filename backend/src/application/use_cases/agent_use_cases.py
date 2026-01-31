"""Use cases for Agent management.

Application layer use cases following clean architecture principles.
"""

from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.agent import Agent
from src.domain.repositories.agent_repository import AgentRepository


class CreateAgentUseCase:
    """エージェント作成ユースケース."""

    def __init__(self, repository: AgentRepository) -> None:
        self.repository = repository

    def execute(
        self,
        user_id: UUID,
        name: str,
        description: str | None = None,
        slack_channel_id: str | None = None,
    ) -> Agent:
        """エージェントを作成する."""
        agent = Agent(
            id=uuid4(),
            user_id=user_id,
            name=name,
            description=description,
            slack_channel_id=slack_channel_id,
            created_at=datetime.now(),
        )
        return self.repository.create(agent)


class GetAgentsUseCase:
    """エージェント一覧取得ユースケース."""

    def __init__(self, repository: AgentRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID) -> list[Agent]:
        """ユーザーの全エージェントを取得する."""
        return self.repository.get_all(user_id)


class GetAgentUseCase:
    """エージェント取得ユースケース."""

    def __init__(self, repository: AgentRepository) -> None:
        self.repository = repository

    def execute(self, agent_id: UUID, user_id: UUID) -> Agent | None:
        """IDでエージェントを取得する."""
        return self.repository.get_by_id(agent_id, user_id)


class UpdateAgentUseCase:
    """エージェント更新ユースケース."""

    def __init__(self, repository: AgentRepository) -> None:
        self.repository = repository

    def execute(
        self,
        agent_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None,
        slack_channel_id: str | None = None,
    ) -> Agent | None:
        """エージェントを更新する."""
        agent = self.repository.get_by_id(agent_id, user_id)
        if not agent:
            return None

        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if slack_channel_id is not None:
            agent.slack_channel_id = slack_channel_id

        agent.updated_at = datetime.now()
        return self.repository.update(agent)


class DeleteAgentUseCase:
    """エージェント削除ユースケース."""

    def __init__(self, repository: AgentRepository) -> None:
        self.repository = repository

    def execute(self, agent_id: UUID, user_id: UUID) -> bool:
        """エージェントを削除する."""
        return self.repository.delete(agent_id, user_id)
