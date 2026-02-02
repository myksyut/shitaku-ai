"""Agent API endpoints.

REST API endpoints for agent management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from src.application.use_cases.agent_use_cases import (
    CreateAgentUseCase,
    DeleteAgentUseCase,
    GetAgentsUseCase,
    GetAgentUseCase,
    UpdateAgentUseCase,
)
from src.application.use_cases.calendar_use_cases import (
    GetMeetingsByAgentUseCase,
    LinkAgentToMeetingUseCase,
    UnlinkAgentFromMeetingUseCase,
)
from src.domain.entities.agent import Agent
from src.domain.entities.recurring_meeting import RecurringMeeting
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)
from src.presentation.api.v1.dependencies import (
    get_current_user_id,
    get_user_supabase_client,
)
from src.presentation.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from src.presentation.schemas.google import (
    AttendeeResponse,
    LinkRecurringMeetingRequest,
    LinkRecurringMeetingResponse,
    RecurringMeetingResponse,
    UnlinkRecurringMeetingResponse,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def get_repository(
    client: Client = Depends(get_user_supabase_client),
) -> AgentRepositoryImpl:
    """リポジトリのDI（ユーザーコンテキスト付きクライアント使用）."""
    return AgentRepositoryImpl(client)


def get_recurring_meeting_repository(
    client: Client = Depends(get_user_supabase_client),
) -> RecurringMeetingRepositoryImpl:
    """定例MTGリポジトリのDI."""
    return RecurringMeetingRepositoryImpl(client)


def _to_response(agent: Agent) -> AgentResponse:
    """エンティティをレスポンスに変換."""
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        slack_channel_id=agent.slack_channel_id,
        transcript_count=agent.transcript_count,
        slack_message_days=agent.slack_message_days,
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


def _to_meeting_response(meeting: RecurringMeeting) -> RecurringMeetingResponse:
    """定例MTGエンティティをレスポンスに変換."""
    return RecurringMeetingResponse(
        id=meeting.id,
        google_event_id=meeting.google_event_id,
        title=meeting.title,
        rrule=meeting.rrule,
        frequency=meeting.frequency.value,
        attendees=[AttendeeResponse(email=a.email, name=a.name) for a in meeting.attendees],
        next_occurrence=meeting.next_occurrence,
        agent_id=meeting.agent_id,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("/{agent_id}/recurring-meetings", response_model=list[RecurringMeetingResponse])
async def get_agent_recurring_meetings(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> list[RecurringMeetingResponse]:
    """エージェントに紐付けられた定例MTG一覧を取得する."""
    use_case = GetMeetingsByAgentUseCase(recurring_meeting_repo)
    meetings = await use_case.execute(agent_id, user_id)
    return [_to_meeting_response(m) for m in meetings]


@router.post("/{agent_id}/recurring-meetings", response_model=LinkRecurringMeetingResponse)
async def link_recurring_meeting(
    agent_id: UUID,
    data: LinkRecurringMeetingRequest,
    user_id: UUID = Depends(get_current_user_id),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> LinkRecurringMeetingResponse:
    """定例MTGをエージェントに紐付ける."""
    use_case = LinkAgentToMeetingUseCase(recurring_meeting_repo)
    try:
        meeting = await use_case.execute(
            meeting_id=data.recurring_meeting_id,
            agent_id=agent_id,
            user_id=user_id,
        )
        return LinkRecurringMeetingResponse(
            message="定例MTGを紐付けました",
            recurring_meeting=_to_meeting_response(meeting),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None


@router.delete(
    "/{agent_id}/recurring-meetings/{meeting_id}",
    response_model=UnlinkRecurringMeetingResponse,
)
async def unlink_recurring_meeting(
    agent_id: UUID,  # noqa: ARG001
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> UnlinkRecurringMeetingResponse:
    """定例MTGとエージェントの紐付けを解除する."""
    unlink_use_case = UnlinkAgentFromMeetingUseCase(recurring_meeting_repo)
    await unlink_use_case.execute(meeting_id, user_id)
    return UnlinkRecurringMeetingResponse(message="紐付けを解除しました")
