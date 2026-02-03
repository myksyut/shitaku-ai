"""Knowledge API endpoints.

REST API endpoints for knowledge management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.use_cases.knowledge_use_cases import (
    DeleteKnowledgeUseCase,
    GetKnowledgeListUseCase,
    GetKnowledgeUseCase,
    UploadKnowledgeUseCase,
)
from src.domain.entities.knowledge import Knowledge
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl
from src.infrastructure.services.normalization_service_impl import NormalizationServiceImpl
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeResponse,
    KnowledgeUploadResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _to_response(knowledge: Knowledge) -> KnowledgeResponse:
    """エンティティをレスポンスに変換."""
    return KnowledgeResponse(
        id=knowledge.id,
        agent_id=knowledge.agent_id,
        original_text=knowledge.original_text,
        normalized_text=knowledge.normalized_text,
        meeting_date=knowledge.meeting_date,
        created_at=knowledge.created_at,
        is_normalized=knowledge.is_normalized(),
    )


@router.post("", response_model=KnowledgeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge(
    data: KnowledgeCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> KnowledgeUploadResponse:
    """ナレッジをアップロードする（正規化処理含む）."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    knowledge_repository = KnowledgeRepositoryImpl(client)
    dictionary_repository = DictionaryRepositoryImpl(client)
    agent_repository = AgentRepositoryImpl(client)
    normalization_service = NormalizationServiceImpl()

    use_case = UploadKnowledgeUseCase(
        knowledge_repository=knowledge_repository,
        dictionary_repository=dictionary_repository,
        agent_repository=agent_repository,
        normalization_service=normalization_service,
    )

    try:
        result = await use_case.execute(
            user_id=user_id,
            agent_id=data.agent_id,
            text=data.text,
        )

        return KnowledgeUploadResponse(
            knowledge=_to_response(result.knowledge),
            normalization_warning=result.normalization_warning,
            replacement_count=result.replacement_count,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("", response_model=list[KnowledgeResponse])
async def get_knowledge_list(
    agent_id: UUID,
    limit: int | None = Query(None, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
) -> list[KnowledgeResponse]:
    """ナレッジ一覧を取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = KnowledgeRepositoryImpl(client)
    use_case = GetKnowledgeListUseCase(repository)
    knowledge_list = await use_case.execute(agent_id, user_id, limit)
    return [_to_response(k) for k in knowledge_list]


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> KnowledgeResponse:
    """ナレッジを取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = KnowledgeRepositoryImpl(client)
    use_case = GetKnowledgeUseCase(repository)
    knowledge = await use_case.execute(knowledge_id, user_id)
    if not knowledge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    return _to_response(knowledge)


@router.delete("/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    knowledge_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """ナレッジを削除する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = KnowledgeRepositoryImpl(client)
    use_case = DeleteKnowledgeUseCase(repository)
    deleted = await use_case.execute(knowledge_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
