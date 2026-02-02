"""Google API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from src.application.use_cases.calendar_use_cases import (
    GetRecurringMeetingsUseCase,
    LinkAgentToMeetingUseCase,
    SyncRecurringMeetingsUseCase,
)
from src.application.use_cases.google_auth_use_cases import (
    DeleteGoogleIntegrationUseCase,
    GetGoogleIntegrationsUseCase,
    HandleGoogleCallbackUseCase,
    RefreshGoogleTokenUseCase,
    StartAdditionalScopesUseCase,
    StartGoogleOAuthUseCase,
)
from src.config import settings
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.google_integration_repository_impl import (
    GoogleIntegrationRepositoryImpl,
)
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.google import (
    GoogleIntegrationResponse,
    GoogleOAuthStartResponse,
    LinkAgentRequest,
    RecurringMeetingResponse,
    RecurringMeetingsResponse,
    SyncResultResponse,
)

router = APIRouter(prefix="/google", tags=["google"])


def get_repository() -> GoogleIntegrationRepositoryImpl:
    """Get Google integration repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return GoogleIntegrationRepositoryImpl()


def get_meeting_repository() -> RecurringMeetingRepositoryImpl:
    """Get recurring meeting repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return RecurringMeetingRepositoryImpl()


@router.get("/auth", response_model=GoogleOAuthStartResponse)
async def start_google_oauth(
    user_id: UUID = Depends(get_current_user_id),
) -> GoogleOAuthStartResponse:
    """Google OAuth認証を開始する.

    Returns:
        GoogleOAuthStartResponse with authorize_url.
    """
    use_case = StartGoogleOAuthUseCase()
    try:
        result = use_case.execute(user_id)
        return GoogleOAuthStartResponse(authorize_url=result.authorize_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
) -> RedirectResponse:
    """Google OAuthコールバックを処理する.

    Args:
        code: OAuth認可コード.
        state: CSRFトークン.
        error: Googleからのエラー（ユーザーが拒否した場合等）.
        repository: Google連携リポジトリ（DI）.

    Returns:
        Redirect to frontend success/error page.
    """
    frontend_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else ""

    # ユーザーが認可をキャンセルした場合
    if error:
        return RedirectResponse(
            url=f"{frontend_url}/google/error?error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    use_case = HandleGoogleCallbackUseCase(repository)

    try:
        integration = await use_case.execute(code=code, state=state)
        # 成功時はフロントエンドにリダイレクト
        return RedirectResponse(
            url=f"{frontend_url}/google/success?email={integration.email}",
            status_code=status.HTTP_302_FOUND,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"{frontend_url}/google/error?error={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/integrations", response_model=list[GoogleIntegrationResponse])
async def get_google_integrations(
    user_id: UUID = Depends(get_current_user_id),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
) -> list[GoogleIntegrationResponse]:
    """ユーザーのGoogle連携一覧を取得する.

    Returns:
        List of GoogleIntegrationResponse.
    """
    use_case = GetGoogleIntegrationsUseCase(repository)
    integrations = await use_case.execute(user_id)
    return [
        GoogleIntegrationResponse(
            id=i.id,
            email=i.email,
            granted_scopes=i.granted_scopes,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in integrations
    ]


@router.delete("/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_google_integration(
    integration_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
) -> None:
    """Google連携を削除する."""
    use_case = DeleteGoogleIntegrationUseCase(repository)
    deleted = await use_case.execute(integration_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )


@router.get("/auth/additional-scopes", response_model=GoogleOAuthStartResponse)
async def start_additional_scopes_oauth(
    integration_id: UUID = Query(..., description="連携ID"),
    user_id: UUID = Depends(get_current_user_id),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
) -> GoogleOAuthStartResponse:
    """追加スコープの認証URLを取得する（Incremental Authorization）.

    Drive/Docs APIへのアクセスに必要な追加スコープを要求する際に使用。

    Args:
        integration_id: 連携ID.
        user_id: ユーザーID（DI）.
        repository: Google連携リポジトリ（DI）.

    Returns:
        GoogleOAuthStartResponse with authorize_url.
    """
    use_case = StartAdditionalScopesUseCase(repository)
    try:
        result = await use_case.execute(user_id, integration_id)
        return GoogleOAuthStartResponse(authorize_url=result.authorize_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Calendar endpoints


@router.get("/calendar/recurring", response_model=RecurringMeetingsResponse)
async def get_recurring_meetings(
    user_id: UUID = Depends(get_current_user_id),
    meeting_repository: RecurringMeetingRepositoryImpl = Depends(get_meeting_repository),
) -> RecurringMeetingsResponse:
    """定例MTG一覧を取得する.

    AC5: 定例MTG一覧表示

    Returns:
        RecurringMeetingsResponse with list of meetings.
    """
    use_case = GetRecurringMeetingsUseCase(meeting_repository)
    meetings = use_case.execute(user_id)
    return RecurringMeetingsResponse(
        meetings=[
            RecurringMeetingResponse(
                id=m.id,
                google_event_id=m.google_event_id,
                title=m.title,
                frequency=m.frequency,
                attendees=m.attendees,
                next_occurrence=m.next_occurrence,
                agent_id=m.agent_id,
            )
            for m in meetings
        ]
    )


@router.post("/calendar/recurring/sync", response_model=SyncResultResponse)
async def sync_recurring_meetings(
    integration_id: UUID = Query(..., description="Google連携ID"),
    user_id: UUID = Depends(get_current_user_id),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
    meeting_repository: RecurringMeetingRepositoryImpl = Depends(get_meeting_repository),
) -> SyncResultResponse:
    """Calendar APIから定例MTGを同期する.

    Returns:
        SyncResultResponse with created and updated counts.
    """
    refresh_use_case = RefreshGoogleTokenUseCase(repository)
    use_case = SyncRecurringMeetingsUseCase(repository, meeting_repository, refresh_use_case)

    try:
        result = await use_case.execute(user_id, integration_id)
        return SyncResultResponse(created=result.created, updated=result.updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/calendar/recurring/{meeting_id}/link-agent")
async def link_agent_to_meeting(
    meeting_id: UUID,
    request: LinkAgentRequest,
    user_id: UUID = Depends(get_current_user_id),
    meeting_repository: RecurringMeetingRepositoryImpl = Depends(get_meeting_repository),
) -> dict[str, bool]:
    """定例MTGにエージェントを紐付ける.

    AC9: エージェント作成画面遷移のための紐付け

    Returns:
        Success status.
    """
    use_case = LinkAgentToMeetingUseCase(meeting_repository)

    try:
        use_case.execute(meeting_id, user_id, request.agent_id)
        return {"linked": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
