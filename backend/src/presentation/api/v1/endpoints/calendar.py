"""Calendar API endpoints.

REST API endpoints for recurring meeting management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from src.application.use_cases.calendar_use_cases import (
    GetRecurringMeetingsUseCase,
    GetUnlinkedMeetingsUseCase,
    SyncRecurringMeetingsUseCase,
)
from src.domain.entities.recurring_meeting import RecurringMeeting
from src.infrastructure.repositories.google_integration_repository_impl import (
    GoogleIntegrationRepositoryImpl,
)
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)
from src.presentation.api.v1.dependencies import (
    get_current_user_id,
    get_user_supabase_client,
)
from src.presentation.schemas.google import (
    AttendeeResponse,
    RecurringMeetingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


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


def _to_response(meeting: RecurringMeeting) -> RecurringMeetingResponse:
    """エンティティをレスポンスに変換."""
    return RecurringMeetingResponse(
        id=meeting.id,
        google_event_id=meeting.google_event_id,
        title=meeting.title,
        rrule=meeting.rrule,
        frequency=meeting.frequency.value,
        attendees=[AttendeeResponse(email=a.email, name=a.name) for a in meeting.attendees],
        next_occurrence=meeting.next_occurrence,
        agent_id=meeting.agent_id,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("/recurring", response_model=list[RecurringMeetingResponse])
async def get_recurring_meetings(
    user_id: UUID = Depends(get_current_user_id),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> list[RecurringMeetingResponse]:
    """同期済み定例MTG一覧を取得する."""
    use_case = GetRecurringMeetingsUseCase(recurring_meeting_repo)
    meetings = await use_case.execute(user_id)
    return [_to_response(m) for m in meetings]


@router.get("/recurring/unlinked", response_model=list[RecurringMeetingResponse])
async def get_unlinked_meetings(
    user_id: UUID = Depends(get_current_user_id),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> list[RecurringMeetingResponse]:
    """エージェント未紐付けの定例MTG一覧を取得する."""
    use_case = GetUnlinkedMeetingsUseCase(recurring_meeting_repo)
    meetings = await use_case.execute(user_id)
    return [_to_response(m) for m in meetings]


@router.post("/sync", response_model=list[RecurringMeetingResponse])
async def sync_recurring_meetings(
    user_id: UUID = Depends(get_current_user_id),
    google_integration_repo: GoogleIntegrationRepositoryImpl = Depends(get_google_integration_repository),
    recurring_meeting_repo: RecurringMeetingRepositoryImpl = Depends(get_recurring_meeting_repository),
) -> list[RecurringMeetingResponse]:
    """Google Calendarから定例MTGを同期する."""
    use_case = SyncRecurringMeetingsUseCase(google_integration_repo, recurring_meeting_repo)
    try:
        meetings = await use_case.execute(user_id)
        return [_to_response(m) for m in meetings]
    except ValueError as e:
        logger.warning(f"Sync failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
