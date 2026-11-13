from uuid import UUID

from fastapi import APIRouter, Depends
from supabase import Client

from src.application.use_cases.team_memory_use_cases import ExtractOccurrenceMemory, TeamMemoryUseCases
from src.domain.entities.series import CreatorAccess, MemberAccess
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.infrastructure.repositories.team_memory_repository_impl import TeamMemoryRepositoryImpl
from src.infrastructure.services.meeting_memory_extractor import MeetingMemoryExtractor
from src.presentation.api.v1.dependencies import (
    creator_access,
    get_series_repository,
    get_user_supabase_client,
    member_access,
)
from src.presentation.schemas.team_memory import (
    ExtractionReport,
    NewMemoryRequest,
    ResolutionRequest,
    TeamMemoryResponse,
    memory_draft,
    memory_response,
)

router = APIRouter(prefix="/series/{series_id}", tags=["memory"])


def get_memory(client: Client = Depends(get_user_supabase_client)) -> TeamMemoryRepositoryImpl:
    """Use the caller's JWT for every memory operation."""
    return TeamMemoryRepositoryImpl(client)


def get_extractor(client: Client = Depends(get_user_supabase_client)) -> ExtractOccurrenceMemory:
    """Keep extraction persistence under the authenticated creator's RLS."""
    return ExtractOccurrenceMemory(
        TeamMemoryRepositoryImpl(client),
        SeriesRepositoryImpl(client),
        KnowledgeRepositoryImpl(client),
        DictionaryRepositoryImpl(client),
        MeetingMemoryExtractor(),
    )


@router.get("/memory")
def get_memory_board(
    access: MemberAccess = Depends(member_access),
    memory: TeamMemoryRepositoryImpl = Depends(get_memory),
    series: SeriesRepositoryImpl = Depends(get_series_repository),
) -> TeamMemoryResponse:
    """Read team decisions, actions and issues."""
    return memory_response(TeamMemoryUseCases(memory, series).board(access))


@router.post("/memory", status_code=201)
def add_memory(
    request: NewMemoryRequest,
    access: CreatorAccess = Depends(creator_access),
    memory: TeamMemoryRepositoryImpl = Depends(get_memory),
    series: SeriesRepositoryImpl = Depends(get_series_repository),
) -> TeamMemoryResponse:
    """Add human-authored team memory."""
    return memory_response(TeamMemoryUseCases(memory, series).add(access, memory_draft(request)))


@router.put("/memory/{item_id}")
def edit_memory(
    item_id: UUID,
    request: NewMemoryRequest,
    access: CreatorAccess = Depends(creator_access),
    memory: TeamMemoryRepositoryImpl = Depends(get_memory),
    series: SeriesRepositoryImpl = Depends(get_series_repository),
) -> TeamMemoryResponse:
    """Edit a same-kind item and protect it from automatic replacement."""
    return memory_response(TeamMemoryUseCases(memory, series).edit(access, item_id, memory_draft(request)))


@router.put("/memory/{item_id}/resolution")
def resolve_memory(
    item_id: UUID,
    request: ResolutionRequest,
    access: MemberAccess = Depends(member_access),
    memory: TeamMemoryRepositoryImpl = Depends(get_memory),
    series: SeriesRepositoryImpl = Depends(get_series_repository),
) -> TeamMemoryResponse:
    """Allow members to change action status, never other memory fields."""
    return memory_response(TeamMemoryUseCases(memory, series).resolve(access, item_id, request.resolution))


@router.delete("/memory/{item_id}")
def delete_memory(
    item_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    memory: TeamMemoryRepositoryImpl = Depends(get_memory),
    series: SeriesRepositoryImpl = Depends(get_series_repository),
) -> TeamMemoryResponse:
    """Delete an item and return the refreshed board."""
    return memory_response(TeamMemoryUseCases(memory, series).delete(access, item_id))


@router.post("/occurrences/{occurrence_id}/extract")
def extract_memory(
    occurrence_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    extractor: ExtractOccurrenceMemory = Depends(get_extractor),
) -> ExtractionReport:
    """Extract one occurrence's minutes with explicit truncation reporting."""
    result = extractor.execute(access, occurrence_id)
    return ExtractionReport(
        created=result.created,
        closed=result.closed,
        truncated=result.truncated,
        items=memory_response(result.items).items,
    )
