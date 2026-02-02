"""Transcript API endpoints.

REST API endpoints for meeting transcript management.
"""

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from src.application.use_cases.transcript_use_cases import (
    CreateTranscriptUseCase,
    DeleteTranscriptUseCase,
    GetPendingTranscriptsUseCase,
    GetTranscriptsByRecurringMeetingUseCase,
    GetTranscriptUseCase,
    LinkTranscriptUseCase,
    SyncTranscriptsUseCase,
)
from src.domain.entities.meeting_transcript import (
    MeetingTranscript,
    TranscriptEntry,
    TranscriptStructuredData,
)
from src.infrastructure.external.encryption import decrypt_google_token
from src.infrastructure.external.google_docs_client import GoogleDocsClient
from src.infrastructure.external.google_drive_client import GoogleDriveClient
from src.infrastructure.external.google_oauth_client import GoogleOAuthClient
from src.infrastructure.repositories.google_integration_repository_impl import (
    GoogleIntegrationRepositoryImpl,
)
from src.infrastructure.repositories.meeting_transcript_repository_impl import (
    MeetingTranscriptRepositoryImpl,
)
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)
from src.presentation.api.v1.dependencies import (
    get_current_user_id,
    get_user_supabase_client,
)
from src.presentation.schemas.transcript import (
    LinkTranscriptRequest,
    SyncResultResponse,
    TranscriptCreate,
    TranscriptEntrySchema,
    TranscriptResponse,
    TranscriptStructuredDataSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


def get_repository(
    client: Client = Depends(get_user_supabase_client),
) -> MeetingTranscriptRepositoryImpl:
    """リポジトリのDI（ユーザーコンテキスト付きクライアント使用）."""
    return MeetingTranscriptRepositoryImpl(client)


def get_google_integration_repository(
    client: Client = Depends(get_user_supabase_client),
) -> GoogleIntegrationRepositoryImpl:
    """Google連携リポジトリのDI."""
    return GoogleIntegrationRepositoryImpl(client)


def get_recurring_meeting_repository(
    client: Client = Depends(get_user_supabase_client),
) -> RecurringMeetingRepositoryImpl:
    """定例MTGリポジトリのDI."""
    return RecurringMeetingRepositoryImpl(client)


def _to_response(transcript: MeetingTranscript) -> TranscriptResponse:
    """エンティティをレスポンスに変換."""
    structured_data_schema: TranscriptStructuredDataSchema | None = None
    if transcript.structured_data is not None:
        structured_data_schema = TranscriptStructuredDataSchema(
            entries=[
                TranscriptEntrySchema(
                    speaker=entry.speaker,
                    timestamp=entry.timestamp,
                    text=entry.text,
                )
                for entry in transcript.structured_data.entries
            ]
        )

    return TranscriptResponse(
        id=transcript.id,
        recurring_meeting_id=transcript.recurring_meeting_id,
        meeting_date=transcript.meeting_date,
        google_doc_id=transcript.google_doc_id,
        raw_text=transcript.raw_text,
        structured_data=structured_data_schema,
        match_confidence=transcript.match_confidence,
        is_auto_linked=transcript.is_auto_linked(),
        needs_manual_confirmation=transcript.needs_manual_confirmation(),
        created_at=transcript.created_at,
    )


def _to_entity(data: TranscriptCreate, transcript_id: UUID) -> MeetingTranscript:
    """リクエストをエンティティに変換."""
    from datetime import UTC, datetime

    structured_data: TranscriptStructuredData | None = None
    if data.structured_data is not None:
        structured_data = TranscriptStructuredData(
            entries=[
                TranscriptEntry(
                    speaker=entry.speaker,
                    timestamp=entry.timestamp,
                    text=entry.text,
                )
                for entry in data.structured_data.entries
            ]
        )

    return MeetingTranscript(
        id=transcript_id,
        recurring_meeting_id=data.recurring_meeting_id,
        meeting_date=data.meeting_date,
        google_doc_id=data.google_doc_id,
        raw_text=data.raw_text,
        structured_data=structured_data,
        match_confidence=data.match_confidence,
        created_at=datetime.now(UTC),
    )


@router.post("", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(
    data: TranscriptCreate,
    repository: MeetingTranscriptRepositoryImpl = Depends(get_repository),
) -> TranscriptResponse:
    """トランスクリプトを作成する."""
    transcript_id = uuid4()
    transcript = _to_entity(data, transcript_id)
    use_case = CreateTranscriptUseCase(repository)
    created = await use_case.execute(transcript)
    return _to_response(created)


@router.get("", response_model=list[TranscriptResponse])
async def get_transcripts(
    recurring_meeting_id: UUID = Query(..., description="定例MTG ID"),
    limit: int | None = Query(None, ge=1, le=100, description="取得件数上限"),
    repository: MeetingTranscriptRepositoryImpl = Depends(get_repository),
) -> list[TranscriptResponse]:
    """定例MTGのトランスクリプト一覧を取得する."""
    use_case = GetTranscriptsByRecurringMeetingUseCase(repository)
    transcripts = await use_case.execute(recurring_meeting_id, limit)
    return [_to_response(t) for t in transcripts]


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: UUID,
    repository: MeetingTranscriptRepositoryImpl = Depends(get_repository),
) -> TranscriptResponse:
    """トランスクリプトを取得する."""
    use_case = GetTranscriptUseCase(repository)
    transcript = await use_case.execute(transcript_id)
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )
    return _to_response(transcript)


@router.delete("/{transcript_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcript(
    transcript_id: UUID,
    repository: MeetingTranscriptRepositoryImpl = Depends(get_repository),
) -> None:
    """トランスクリプトを削除する."""
    use_case = DeleteTranscriptUseCase(repository)
    deleted = await use_case.execute(transcript_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )


@router.post("/sync", response_model=SyncResultResponse)
async def sync_transcripts(
    user_id: UUID = Depends(get_current_user_id),
    transcript_repo: MeetingTranscriptRepositoryImpl = Depends(get_repository),
    google_integration_repo: GoogleIntegrationRepositoryImpl = Depends(get_google_integration_repository),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> SyncResultResponse:
    """Google DriveからトランスクリプトをDriveからト同期する.

    Meet Recordingsフォルダからトランスクリプトファイルを取得し、
    定例MTGとのマッチングを行ってDBに保存する。
    """
    # Google連携からアクセストークンを取得
    integrations = await google_integration_repo.get_all(user_id)
    if not integrations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google integration found. Please connect Google first.",
        )

    integration = integrations[0]

    # Drive/Docsスコープの確認
    drive_scope = "https://www.googleapis.com/auth/drive.readonly"
    docs_scope = "https://www.googleapis.com/auth/documents.readonly"
    if not integration.has_scope(drive_scope) or not integration.has_scope(docs_scope):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drive or Docs scope not granted. Please reconnect Google.",
        )

    # アクセストークンを取得
    try:
        refresh_token = decrypt_google_token(integration.encrypted_refresh_token)
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt Google token. Please reconnect.",
        ) from None

    oauth_client = GoogleOAuthClient()
    try:
        token_response = await oauth_client.refresh_access_token(refresh_token)
    except ValueError as e:
        logger.error(f"Failed to refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refresh Google token. Please reconnect.",
        ) from None

    # Google Drive/Docsクライアントを作成
    drive_client = GoogleDriveClient(token_response.access_token)
    docs_client = GoogleDocsClient(token_response.access_token)

    # 同期実行
    use_case = SyncTranscriptsUseCase(
        transcript_repository=transcript_repo,
        recurring_meeting_repository=recurring_meeting_repo,
        drive_client=drive_client,
        docs_client=docs_client,
    )

    try:
        result = await use_case.execute(user_id)
    except ValueError as e:
        logger.warning(f"Sync failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return SyncResultResponse(
        synced_count=result.synced_count,
        skipped_count=result.skipped_count,
        error_count=result.error_count,
        synced_transcripts=[_to_response(t) for t in result.synced_transcripts],
    )


@router.post("/{transcript_id}/link", response_model=TranscriptResponse)
async def link_transcript(
    transcript_id: UUID,
    data: LinkTranscriptRequest,
    user_id: UUID = Depends(get_current_user_id),
    transcript_repo: MeetingTranscriptRepositoryImpl = Depends(get_repository),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> TranscriptResponse:
    """トランスクリプトを定例MTGに手動紐付けする.

    信頼度が低かったトランスクリプトを手動で定例MTGに紐付ける。
    紐付け後の信頼度は1.0に設定される。
    """
    use_case = LinkTranscriptUseCase(transcript_repo, recurring_meeting_repo)

    try:
        transcript = await use_case.execute(
            transcript_id=transcript_id,
            recurring_meeting_id=data.recurring_meeting_id,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None

    return _to_response(transcript)


@router.get("/pending", response_model=list[TranscriptResponse])
async def get_pending_transcripts(
    user_id: UUID = Depends(get_current_user_id),
    repository: MeetingTranscriptRepositoryImpl = Depends(get_repository),
) -> list[TranscriptResponse]:
    """手動確認が必要なトランスクリプト一覧を取得する.

    信頼度が0.7未満のトランスクリプトを返す。
    """
    use_case = GetPendingTranscriptsUseCase(repository)
    transcripts = await use_case.execute(user_id)
    return [_to_response(t) for t in transcripts]
