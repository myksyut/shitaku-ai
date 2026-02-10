"""Slack API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from slack_sdk.errors import SlackApiError
from supabase import Client

from src.application.use_cases.slack_use_cases import (
    DeleteSlackIntegrationUseCase,
    GetSlackChannelsUseCase,
    GetSlackIntegrationsUseCase,
    GetSlackMessagesUseCase,
    HandleSlackCallbackUseCase,
    StartSlackOAuthUseCase,
)
from src.config import settings
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.oauth_state_repository_impl import (
    OAuthStateRepositoryImpl,
)
from src.infrastructure.repositories.slack_integration_repository_impl import (
    SlackIntegrationRepositoryImpl,
)
from src.presentation.api.v1.dependencies import (
    get_current_user_id,
    get_user_supabase_client,
)
from src.presentation.schemas.slack import (
    SlackChannelResponse,
    SlackIntegrationResponse,
    SlackMessageResponse,
    SlackOAuthStartResponse,
)

router = APIRouter(prefix="/slack", tags=["slack"])


def get_repository(
    client: Client = Depends(get_user_supabase_client),
) -> SlackIntegrationRepositoryImpl:
    """Get Slack integration repository instance with user context."""
    return SlackIntegrationRepositoryImpl(client)


def get_callback_repository() -> SlackIntegrationRepositoryImpl:
    """Get repository for OAuth callback (uses service role, no user context).

    OAuth callback is called by Slack, not authenticated user.
    """
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return SlackIntegrationRepositoryImpl(client)


def get_oauth_state_repository(
    client: Client = Depends(get_user_supabase_client),
) -> OAuthStateRepositoryImpl:
    """Get OAuth state repository with user context for /auth endpoint."""
    return OAuthStateRepositoryImpl(client)


def get_callback_oauth_state_repository() -> OAuthStateRepositoryImpl:
    """Get OAuth state repository for callback (uses service role, RLS bypass).

    OAuth callback needs to access state created by any user.
    """
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return OAuthStateRepositoryImpl(client)


@router.get("/auth", response_model=SlackOAuthStartResponse)
async def start_slack_oauth(
    user_id: UUID = Depends(get_current_user_id),
    oauth_state_repository: OAuthStateRepositoryImpl = Depends(get_oauth_state_repository),
    redirect_origin: str | None = Query(None, description="callback後のリダイレクト先オリジン"),
) -> SlackOAuthStartResponse:
    """Slack OAuth認証を開始する.

    Returns:
        SlackOAuthStartResponse with authorize_url.
    """
    # redirect_originをBACKEND_CORS_ORIGINSでバリデーション（オープンリダイレクト防止）
    validated_origin: str | None = None
    if redirect_origin and redirect_origin in settings.BACKEND_CORS_ORIGINS:
        validated_origin = redirect_origin

    use_case = StartSlackOAuthUseCase(oauth_state_repository)
    try:
        result = await use_case.execute(user_id, redirect_origin=validated_origin)
        return SlackOAuthStartResponse(authorize_url=result.authorize_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/callback")
async def slack_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    repository: SlackIntegrationRepositoryImpl = Depends(get_callback_repository),
    oauth_state_repository: OAuthStateRepositoryImpl = Depends(get_callback_oauth_state_repository),
) -> RedirectResponse:
    """Slack OAuthコールバックを処理する.

    Args:
        code: OAuth認可コード.
        state: CSRFトークン.
        repository: Slack連携リポジトリ（DI）.
        oauth_state_repository: OAuth stateリポジトリ（DI）.

    Returns:
        Redirect to frontend success page.
    """
    fallback_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else ""
    use_case = HandleSlackCallbackUseCase(repository, oauth_state_repository)

    try:
        integration, oauth_state = await use_case.execute(code=code, state=state)
        # stateに保存されたredirect_originを使用、なければフォールバック
        frontend_url = oauth_state.redirect_origin or fallback_url
        redirect_url = f"{frontend_url}/settings/slack?success=true&workspace={integration.workspace_name}"
        return RedirectResponse(url=redirect_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/integrations", response_model=list[SlackIntegrationResponse])
async def get_slack_integrations(
    user_id: UUID = Depends(get_current_user_id),
    repository: SlackIntegrationRepositoryImpl = Depends(get_repository),
) -> list[SlackIntegrationResponse]:
    """ユーザーのSlack連携一覧を取得する.

    Returns:
        List of SlackIntegrationResponse.
    """
    use_case = GetSlackIntegrationsUseCase(repository)
    integrations = await use_case.execute(user_id)
    return [
        SlackIntegrationResponse(
            id=i.id,
            workspace_id=i.workspace_id,
            workspace_name=i.workspace_name,
            created_at=i.created_at,
        )
        for i in integrations
    ]


@router.delete("/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slack_integration(
    integration_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: SlackIntegrationRepositoryImpl = Depends(get_repository),
) -> None:
    """Slack連携を削除する."""
    use_case = DeleteSlackIntegrationUseCase(repository)
    deleted = await use_case.execute(integration_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )


@router.get(
    "/integrations/{integration_id}/channels",
    response_model=list[SlackChannelResponse],
)
async def get_slack_channels(
    integration_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: SlackIntegrationRepositoryImpl = Depends(get_repository),
) -> list[SlackChannelResponse]:
    """Slackチャンネル一覧を取得する.

    Args:
        integration_id: 連携ID.
        user_id: ユーザーID（DI）.
        repository: Slack連携リポジトリ（DI）.

    Returns:
        List of SlackChannelResponse.
    """
    use_case = GetSlackChannelsUseCase(repository)

    try:
        channels = await use_case.execute(user_id, integration_id)
        return [SlackChannelResponse(id=c.id, name=c.name) for c in channels]
    except SlackApiError as e:
        if e.response.get("error") == "ratelimited":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Slack API rate limit exceeded. Please try again later.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Slack API error: {e.response.get('error', 'unknown')}",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/integrations/{integration_id}/channels/{channel_id}/messages",
    response_model=list[SlackMessageResponse],
)
async def get_slack_messages(
    integration_id: UUID,
    channel_id: str,
    oldest: datetime = Query(..., description="取得開始日時（ISO8601形式）"),
    latest: datetime | None = Query(None, description="取得終了日時（ISO8601形式、省略時は現在）"),
    user_id: UUID = Depends(get_current_user_id),
    repository: SlackIntegrationRepositoryImpl = Depends(get_repository),
) -> list[SlackMessageResponse]:
    """期間指定でSlackメッセージを取得する.

    Args:
        integration_id: 連携ID.
        channel_id: チャンネルID.
        oldest: 取得開始日時.
        latest: 取得終了日時（省略時は現在）.
        user_id: ユーザーID（DI）.
        repository: Slack連携リポジトリ（DI）.

    Returns:
        List of SlackMessageResponse.
    """
    use_case = GetSlackMessagesUseCase(repository)

    try:
        messages = await use_case.execute(
            user_id=user_id,
            integration_id=integration_id,
            channel_id=channel_id,
            oldest=oldest,
            latest=latest,
        )
        return [
            SlackMessageResponse(
                user_name=m.user_name,
                text=m.text,
                posted_at=m.posted_at.isoformat(),
            )
            for m in messages
        ]
    except SlackApiError as e:
        if e.response.get("error") == "ratelimited":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Slack API rate limit exceeded. Please try again later.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Slack API error: {e.response.get('error', 'unknown')}",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
