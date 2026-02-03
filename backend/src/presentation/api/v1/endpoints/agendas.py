"""Agenda API endpoints.

REST API endpoints for agenda management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.use_cases.agenda_use_cases import (
    DeleteAgendaUseCase,
    GenerateAgendaUseCase,
    GetAgendasUseCase,
    GetAgendaUseCase,
    UpdateAgendaUseCase,
)
from src.domain.entities.agenda import Agenda
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.agenda_repository_impl import AgendaRepositoryImpl
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl
from src.infrastructure.repositories.meeting_transcript_repository_impl import (
    MeetingTranscriptRepositoryImpl,
)
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)
from src.infrastructure.repositories.slack_integration_repository_impl import (
    SlackIntegrationRepositoryImpl,
)
from src.infrastructure.services.agenda_generation_service import AgendaGenerationService
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.agenda import (
    AgendaGenerateRequest,
    AgendaGenerateResponse,
    AgendaResponse,
    AgendaUpdate,
    DataSourcesInfo,
)

router = APIRouter(prefix="/agendas", tags=["agendas"])


def _to_response(agenda: Agenda) -> AgendaResponse:
    """エンティティをレスポンスに変換."""
    return AgendaResponse(
        id=agenda.id,
        agent_id=agenda.agent_id,
        content=agenda.content,
        source_knowledge_id=agenda.source_knowledge_id,
        generated_at=agenda.generated_at,
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.post("/generate", response_model=AgendaGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_agenda(
    data: AgendaGenerateRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> AgendaGenerateResponse:
    """アジェンダを生成する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    agenda_repository = AgendaRepositoryImpl(client)
    agent_repository = AgentRepositoryImpl(client)
    knowledge_repository = KnowledgeRepositoryImpl(client)
    dictionary_repository = DictionaryRepositoryImpl(client)
    slack_repository = SlackIntegrationRepositoryImpl(client)
    recurring_meeting_repository = RecurringMeetingRepositoryImpl(client)
    meeting_transcript_repository = MeetingTranscriptRepositoryImpl(client)
    generation_service = AgendaGenerationService()

    use_case = GenerateAgendaUseCase(
        agenda_repository=agenda_repository,
        agent_repository=agent_repository,
        knowledge_repository=knowledge_repository,
        dictionary_repository=dictionary_repository,
        slack_repository=slack_repository,
        generation_service=generation_service,
        recurring_meeting_repository=recurring_meeting_repository,
        meeting_transcript_repository=meeting_transcript_repository,
    )

    try:
        result = await use_case.execute(user_id, data.agent_id)
        return AgendaGenerateResponse(
            agenda=_to_response(result.agenda),
            data_sources=DataSourcesInfo(
                has_knowledge=result.has_knowledge,
                has_slack_messages=result.has_slack_messages,
                slack_message_count=result.slack_message_count,
                dictionary_entry_count=result.dictionary_entry_count,
                has_transcripts=result.has_transcripts,
                transcript_count=result.transcript_count,
                slack_error=result.slack_error,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agenda generation timed out",
        ) from e


@router.get("", response_model=list[AgendaResponse])
async def get_agendas(
    agent_id: UUID,
    limit: int | None = Query(None, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
) -> list[AgendaResponse]:
    """アジェンダ一覧を取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    repository = AgendaRepositoryImpl(client)
    use_case = GetAgendasUseCase(repository)
    agendas = await use_case.execute(agent_id, user_id, limit)
    return [_to_response(a) for a in agendas]


@router.get("/{agenda_id}", response_model=AgendaResponse)
async def get_agenda(
    agenda_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> AgendaResponse:
    """アジェンダを取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    repository = AgendaRepositoryImpl(client)
    use_case = GetAgendaUseCase(repository)
    agenda = await use_case.execute(agenda_id, user_id)
    if not agenda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agenda not found")
    return _to_response(agenda)


@router.put("/{agenda_id}", response_model=AgendaResponse)
async def update_agenda(
    agenda_id: UUID,
    data: AgendaUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> AgendaResponse:
    """アジェンダを更新する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    repository = AgendaRepositoryImpl(client)
    use_case = UpdateAgendaUseCase(repository)
    agenda = await use_case.execute(agenda_id, user_id, data.content)
    if not agenda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agenda not found")
    return _to_response(agenda)


@router.delete("/{agenda_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agenda(
    agenda_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """アジェンダを削除する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    repository = AgendaRepositoryImpl(client)
    use_case = DeleteAgendaUseCase(repository)
    deleted = await use_case.execute(agenda_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agenda not found")
