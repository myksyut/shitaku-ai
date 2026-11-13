from uuid import UUID

from fastapi import APIRouter, Depends
from supabase import Client

from src.application.use_cases.agenda_use_cases import GenerateAgenda
from src.application.use_cases.occurrence_use_cases import OccurrenceUseCases, TranscriptCandidate
from src.domain.entities.series import CreatorAccess, MemberAccess, OccurrenceSummary
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import SeriesCredentials
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl
from src.infrastructure.repositories.occurrence_repository_impl import OccurrenceRepositoryImpl
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.infrastructure.repositories.team_memory_repository_impl import TeamMemoryRepositoryImpl
from src.infrastructure.services.agenda_generation_service import AgendaGenerationService
from src.infrastructure.services.normalization_service_impl import NormalizationServiceImpl
from src.presentation.api.v1.dependencies import (
    creator_access,
    get_series_credentials,
    get_user_supabase_client,
    member_access,
)
from src.presentation.schemas.occurrence import (
    AddKnowledgeRequest,
    AddKnowledgeResponse,
    AgendaRequest,
    AgendaView,
    GenerateAgendaResponse,
    KnowledgeSummary,
    KnowledgeView,
    OccurrenceDetail,
    TopicRequest,
    TopicView,
    UploadRequest,
)

router = APIRouter(prefix="/series/{series_id}", tags=["occurrences"])


def get_content(
    client: Client = Depends(get_user_supabase_client), credentials: SeriesCredentials = Depends(get_series_credentials)
) -> OccurrenceUseCases:
    """Compose caller-scoped content persistence and creator-bound sources."""
    return OccurrenceUseCases(
        SeriesRepositoryImpl(client),
        OccurrenceRepositoryImpl(client),
        KnowledgeRepositoryImpl(client),
        DictionaryRepositoryImpl(client),
        credentials,
        NormalizationServiceImpl(),
    )


def get_generator(
    client: Client = Depends(get_user_supabase_client), credentials: SeriesCredentials = Depends(get_series_credentials)
) -> GenerateAgenda:
    """Use privileged access only inside the calendar mirror."""
    return GenerateAgenda(
        SeriesRepositoryImpl(client),
        OccurrenceRepositoryImpl(client),
        TeamMemoryRepositoryImpl(client),
        KnowledgeRepositoryImpl(client),
        DictionaryRepositoryImpl(client),
        credentials,
        SeriesCalendarMirror.create(),
        AgendaGenerationService(),
    )


@router.get("/occurrences/{occurrence_id}")
def occurrence_detail(
    occurrence_id: UUID,
    access: MemberAccess = Depends(member_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> OccurrenceDetail:
    """Read shared content for one series occurrence."""
    result = use_cases.detail(access, occurrence_id)
    return OccurrenceDetail(
        occurrence=OccurrenceSummary.of(result.occurrence),
        agenda=AgendaView.model_validate(result.agenda) if result.agenda else None,
        topics=[TopicView.of(t, access.user_id) for t in result.topics],
        knowledge=[KnowledgeSummary.of(k) for k in result.knowledge],
    )


@router.post("/occurrences/{occurrence_id}/topics", status_code=201)
def submit_topic(
    occurrence_id: UUID,
    request: TopicRequest,
    access: MemberAccess = Depends(member_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> TopicView:
    """Post the caller's own suggestion for a future meeting."""
    return TopicView.of(use_cases.submit_topic(access, occurrence_id, request.title, request.details), access.user_id)


@router.delete("/topics/{topic_id}", status_code=204)
def delete_topic(
    topic_id: UUID, access: MemberAccess = Depends(member_access), use_cases: OccurrenceUseCases = Depends(get_content)
) -> None:
    """Withdraw a topic as its author or the series creator."""
    use_cases.delete_topic(access, topic_id)


@router.get("/occurrences/{occurrence_id}/transcript-candidates")
def transcript_candidates(
    occurrence_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> dict[str, list[TranscriptCandidate]]:
    """Read creator Drive candidates live; unpicked files are never stored."""
    return {"candidates": use_cases.transcript_candidates(access, occurrence_id)}


@router.post("/occurrences/{occurrence_id}/knowledge", status_code=201)
def add_knowledge(
    occurrence_id: UUID,
    request: AddKnowledgeRequest,
    access: CreatorAccess = Depends(creator_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> AddKnowledgeResponse:
    """Share an upload or one explicitly selected transcript."""
    if isinstance(request, UploadRequest):
        result = use_cases.add_upload(access, occurrence_id, request.text)
    else:
        result = use_cases.add_transcript(access, occurrence_id, request.google_doc_id)
    return AddKnowledgeResponse(
        knowledge=KnowledgeSummary.of(result.knowledge),
        normalization_warning=result.normalization_warning,
        replacement_count=result.replacement_count,
    )


@router.get("/knowledge/{knowledge_id}")
def get_knowledge(
    knowledge_id: UUID,
    access: MemberAccess = Depends(member_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> KnowledgeView:
    """Read only a selected shared document."""
    knowledge = use_cases.get_knowledge(access, knowledge_id)
    return KnowledgeView(**KnowledgeSummary.of(knowledge).model_dump(), text=knowledge.normalized_text)


@router.delete("/knowledge/{knowledge_id}", status_code=204)
def delete_knowledge(
    knowledge_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> None:
    """Remove creator-selected shared content."""
    use_cases.delete_knowledge(access, knowledge_id)


@router.post("/occurrences/{occurrence_id}/agenda")
def generate_agenda(
    occurrence_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    generator: GenerateAgenda = Depends(get_generator),
) -> GenerateAgendaResponse:
    """Persist required sections even if the proposal model produces no useful text."""
    result = generator.execute(access, occurrence_id)
    return GenerateAgendaResponse(agenda=AgendaView.model_validate(result.agenda), sources=result.sources)


@router.put("/occurrences/{occurrence_id}/agenda")
def save_agenda(
    occurrence_id: UUID,
    request: AgendaRequest,
    access: CreatorAccess = Depends(creator_access),
    use_cases: OccurrenceUseCases = Depends(get_content),
) -> AgendaView:
    """Save a creator's edits to the existing agenda."""
    return AgendaView.model_validate(use_cases.save_agenda(access, occurrence_id, request.content))
