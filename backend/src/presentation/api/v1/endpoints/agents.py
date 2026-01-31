"""Agent API endpoints.

REST API endpoints for agent management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.agent_use_cases import (
    CreateAgentUseCase,
    DeleteAgentUseCase,
    GetAgentsUseCase,
    GetAgentUseCase,
    UpdateAgentUseCase,
)
from src.domain.entities.agent import Agent
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.agent import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


def get_repository() -> AgentRepositoryImpl:
    """リポジトリのDI."""
    return AgentRepositoryImpl()


def _to_response(agent: Agent) -> AgentResponse:
    """エンティティをレスポンスに変換."""
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        slack_channel_id=agent.slack_channel_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    data: AgentCreate,
    user_id: UUID = Depends(get_current_user_id),
    repository: AgentRepositoryImpl = Depends(get_repository),
) -> AgentResponse:
    """エージェントを作成する."""
    use_case = CreateAgentUseCase(repository)
    agent = use_case.execute(
        user_id=user_id,
        name=data.name,
        description=data.description,
        slack_channel_id=data.slack_channel_id,
    )
    return _to_response(agent)


@router.get("", response_model=list[AgentResponse])
def get_agents(
    user_id: UUID = Depends(get_current_user_id),
    repository: AgentRepositoryImpl = Depends(get_repository),
) -> list[AgentResponse]:
    """エージェント一覧を取得する."""
    use_case = GetAgentsUseCase(repository)
    agents = use_case.execute(user_id)
    return [_to_response(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: AgentRepositoryImpl = Depends(get_repository),
) -> AgentResponse:
    """エージェントを取得する."""
    use_case = GetAgentUseCase(repository)
    agent = use_case.execute(agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _to_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    user_id: UUID = Depends(get_current_user_id),
    repository: AgentRepositoryImpl = Depends(get_repository),
) -> AgentResponse:
    """エージェントを更新する."""
    use_case = UpdateAgentUseCase(repository)
    agent = use_case.execute(
        agent_id=agent_id,
        user_id=user_id,
        name=data.name,
        description=data.description,
        slack_channel_id=data.slack_channel_id,
    )
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _to_response(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: AgentRepositoryImpl = Depends(get_repository),
) -> None:
    """エージェントを削除する."""
    use_case = DeleteAgentUseCase(repository)
    deleted = use_case.execute(agent_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
