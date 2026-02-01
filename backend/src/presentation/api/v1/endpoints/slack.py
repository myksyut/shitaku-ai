"""Slack API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

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
from src.infrastructure.repositories.slack_integration_repository_impl import (
    SlackIntegrationRepositoryImpl,
)
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.slack import (
    SlackChannelResponse,
    SlackIntegrationResponse,
    SlackMessageResponse,
    SlackOAuthStartResponse,
)

router = APIRouter(prefix="/slack", tags=["slack"])


def get_repository() -> SlackIntegrationRepositoryImpl:
    """Get Slack integration repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return SlackIntegrationRepositoryImpl()


@router.get("/auth", response_model=SlackOAuthStartResponse)
async def start_slack_oauth(
    user_id: UUID = Depends(get_current_user_id),
) -> SlackOAuthStartResponse:
    """Slack OAuth認証を開始する.

    Returns:
        SlackOAuthStartResponse with authorize_url.
    """
    use_case = StartSlackOAuthUseCase()
    try:
        result = use_case.execute(user_id)
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
    repository: SlackIntegrationRepositoryImpl = Depends(get_repository),
) -> RedirectResponse:
    """Slack OAuthコールバックを処理する.

    Args:
        code: OAuth認可コード.
        state: CSRFトークン.
        repository: Slack連携リポジトリ（DI）.

    Returns:
        Redirect to frontend success page.
    """
    use_case = HandleSlackCallbackUseCase(repository)

    try:
        integration = await use_case.execute(code=code, state=state)
        # 成功時はフロントエンドにリダイレクト
        frontend_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else ""
        return RedirectResponse(url=f"{frontend_url}/slack/success?workspace={integration.workspace_name}")
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
