"""MeetingNote API endpoints.

REST API endpoints for meeting note management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.use_cases.meeting_note_use_cases import (
    DeleteMeetingNoteUseCase,
    GetMeetingNotesUseCase,
    GetMeetingNoteUseCase,
    UploadMeetingNoteUseCase,
)
from src.domain.entities.meeting_note import MeetingNote
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.meeting_note_repository_impl import MeetingNoteRepositoryImpl
from src.infrastructure.services.normalization_service_impl import NormalizationServiceImpl
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.meeting_note import (
    MeetingNoteCreate,
    MeetingNoteResponse,
    MeetingNoteUploadResponse,
)

router = APIRouter(prefix="/meeting-notes", tags=["meeting-notes"])


def _to_response(note: MeetingNote) -> MeetingNoteResponse:
    """エンティティをレスポンスに変換."""
    return MeetingNoteResponse(
        id=note.id,
        agent_id=note.agent_id,
        original_text=note.original_text,
        normalized_text=note.normalized_text,
        meeting_date=note.meeting_date,
        created_at=note.created_at,
        is_normalized=note.is_normalized(),
    )


@router.post("", response_model=MeetingNoteUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting_note(
    data: MeetingNoteCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> MeetingNoteUploadResponse:
    """議事録をアップロードする（正規化処理含む）."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    note_repository = MeetingNoteRepositoryImpl(client)
    dictionary_repository = DictionaryRepositoryImpl(client)
    agent_repository = AgentRepositoryImpl()
    normalization_service = NormalizationServiceImpl()

    use_case = UploadMeetingNoteUseCase(
        note_repository=note_repository,
        dictionary_repository=dictionary_repository,
        agent_repository=agent_repository,
        normalization_service=normalization_service,
    )

    try:
        result = await use_case.execute(
            user_id=user_id,
            agent_id=data.agent_id,
            text=data.text,
            meeting_date=data.meeting_date,
        )

        return MeetingNoteUploadResponse(
            note=_to_response(result.note),
            normalization_warning=result.normalization_warning,
            replacement_count=result.replacement_count,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("", response_model=list[MeetingNoteResponse])
async def get_meeting_notes(
    agent_id: UUID,
    limit: int | None = Query(None, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
) -> list[MeetingNoteResponse]:
    """議事録一覧を取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = MeetingNoteRepositoryImpl(client)
    use_case = GetMeetingNotesUseCase(repository)
    notes = await use_case.execute(agent_id, user_id, limit)
    return [_to_response(n) for n in notes]


@router.get("/{note_id}", response_model=MeetingNoteResponse)
async def get_meeting_note(
    note_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> MeetingNoteResponse:
    """議事録を取得する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = MeetingNoteRepositoryImpl(client)
    use_case = GetMeetingNoteUseCase(repository)
    note = await use_case.execute(note_id, user_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
    return _to_response(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_note(
    note_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """議事録を削除する."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )

    repository = MeetingNoteRepositoryImpl(client)
    use_case = DeleteMeetingNoteUseCase(repository)
    deleted = await use_case.execute(note_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
