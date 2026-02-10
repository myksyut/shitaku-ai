"""Google API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from supabase import Client

from src.application.use_cases.google_auth_use_cases import (
    DeleteGoogleIntegrationUseCase,
    GetGoogleIntegrationsUseCase,
    HandleGoogleCallbackUseCase,
    StartAdditionalScopesUseCase,
    StartGoogleOAuthUseCase,
    SyncProviderTokenUseCase,
)
from src.config import settings
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.google_integration_repository_impl import (
    GoogleIntegrationRepositoryImpl,
)
from src.infrastructure.repositories.oauth_state_repository_impl import (
    OAuthStateRepositoryImpl,
)
from src.presentation.api.v1.dependencies import (
    get_current_user_id,
    get_user_supabase_client,
)
from src.presentation.schemas.google import (
    GoogleIntegrationResponse,
    GoogleOAuthStartResponse,
    SyncProviderTokenRequest,
    SyncProviderTokenResponse,
)

router = APIRouter(prefix="/google", tags=["google"])


def get_repository(
    client: Client = Depends(get_user_supabase_client),
) -> GoogleIntegrationRepositoryImpl:
    """Get Google integration repository instance with user context."""
    return GoogleIntegrationRepositoryImpl(client)


def get_callback_repository() -> GoogleIntegrationRepositoryImpl:
    """Get repository for OAuth callback (uses service role, no user context).

    OAuth callback is called by Google, not authenticated user.
    """
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return GoogleIntegrationRepositoryImpl(client)


def get_oauth_state_repository(
    client: Client = Depends(get_user_supabase_client),
) -> OAuthStateRepositoryImpl:
    """Get OAuth state repository instance with user context."""
    return OAuthStateRepositoryImpl(client)


def get_callback_oauth_state_repository() -> OAuthStateRepositoryImpl:
    """Get OAuth state repository for callback (uses service role, no user context).

    OAuth callback is called by Google, not authenticated user.
    """
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return OAuthStateRepositoryImpl(client)


@router.get("/auth", response_model=GoogleOAuthStartResponse)
async def start_google_oauth(
    user_id: UUID = Depends(get_current_user_id),
    oauth_state_repository: OAuthStateRepositoryImpl = Depends(get_oauth_state_repository),
    redirect_origin: str | None = Query(None, description="callback後のリダイレクト先オリジン"),
) -> GoogleOAuthStartResponse:
    """Google OAuth認証を開始する.

    Returns:
        GoogleOAuthStartResponse with authorize_url.
    """
    # redirect_originをBACKEND_CORS_ORIGINSでバリデーション（オープンリダイレクト防止）
    validated_origin: str | None = None
    if redirect_origin and redirect_origin in settings.BACKEND_CORS_ORIGINS:
        validated_origin = redirect_origin

    use_case = StartGoogleOAuthUseCase(oauth_state_repository)
    try:
        result = await use_case.execute(user_id, redirect_origin=validated_origin)
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
    repository: GoogleIntegrationRepositoryImpl = Depends(get_callback_repository),
    oauth_state_repository: OAuthStateRepositoryImpl = Depends(get_callback_oauth_state_repository),
) -> RedirectResponse:
    """Google OAuthコールバックを処理する.

    Args:
        code: OAuth認可コード.
        state: CSRFトークン.
        error: Googleからのエラー（ユーザーが拒否した場合等）.
        repository: Google連携リポジトリ（DI）.
        oauth_state_repository: OAuth stateリポジトリ（DI）.

    Returns:
        Redirect to frontend success/error page.
    """
    fallback_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else ""

    # ユーザーが認可をキャンセルした場合（stateからredirect_originを取得できないためフォールバック使用）
    if error:
        return RedirectResponse(
            url=f"{fallback_url}/google/error?error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    use_case = HandleGoogleCallbackUseCase(repository, oauth_state_repository)

    try:
        integration, oauth_state = await use_case.execute(code=code, state=state)
        # stateに保存されたredirect_originを使用、なければフォールバック
        frontend_url = oauth_state.redirect_origin or fallback_url
        return RedirectResponse(
            url=f"{frontend_url}/settings/google?success=true&email={integration.email}",
            status_code=status.HTTP_302_FOUND,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"{fallback_url}/settings/google?error={str(e)}",
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
    oauth_state_repository: OAuthStateRepositoryImpl = Depends(get_oauth_state_repository),
    redirect_origin: str | None = Query(None, description="callback後のリダイレクト先オリジン"),
) -> GoogleOAuthStartResponse:
    """追加スコープの認証URLを取得する（Incremental Authorization）.

    Drive/Docs APIへのアクセスに必要な追加スコープを要求する際に使用。

    Args:
        integration_id: 連携ID.
        user_id: ユーザーID（DI）.
        repository: Google連携リポジトリ（DI）.
        oauth_state_repository: OAuth stateリポジトリ（DI）.
        redirect_origin: callback後のリダイレクト先オリジン.

    Returns:
        GoogleOAuthStartResponse with authorize_url.
    """
    # redirect_originをBACKEND_CORS_ORIGINSでバリデーション（オープンリダイレクト防止）
    validated_origin: str | None = None
    if redirect_origin and redirect_origin in settings.BACKEND_CORS_ORIGINS:
        validated_origin = redirect_origin

    use_case = StartAdditionalScopesUseCase(repository, oauth_state_repository)
    try:
        result = await use_case.execute(user_id, integration_id, redirect_origin=validated_origin)
        return GoogleOAuthStartResponse(authorize_url=result.authorize_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/sync-token", response_model=SyncProviderTokenResponse)
async def sync_provider_token(
    request: SyncProviderTokenRequest,
    user_id: UUID = Depends(get_current_user_id),
    repository: GoogleIntegrationRepositoryImpl = Depends(get_repository),
) -> SyncProviderTokenResponse:
    """Supabase AuthのproviderTokenを同期する.

    Google SSOでログイン後、provider_refresh_tokenをバックエンドに保存し、
    Calendar API等へのアクセスを可能にする。

    Args:
        request: SyncProviderTokenRequest.
        user_id: ユーザーID（DI）.
        repository: Google連携リポジトリ（DI）.

    Returns:
        SyncProviderTokenResponse.
    """
    use_case = SyncProviderTokenUseCase(repository)
    result = await use_case.execute(
        user_id=user_id,
        email=request.email,
        provider_refresh_token=request.provider_refresh_token,
        scopes=request.scopes,
    )
    return SyncProviderTokenResponse(
        success=result.success,
        message=result.message,
        integration_id=result.integration_id,
    )
