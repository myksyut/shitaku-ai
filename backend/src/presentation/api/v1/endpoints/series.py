from uuid import UUID

from fastapi import APIRouter, Depends, Response

from src.application.use_cases.series_use_cases import CalendarUseCases, SeriesUseCases
from src.domain.entities.series import (
    CalendarEventChoice,
    CreatorAccess,
    MemberAccess,
    SeriesDetail,
    SeriesError,
    SeriesSettings,
    SeriesSummary,
)
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import SeriesCredentials
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.presentation.api.v1.dependencies import (
    creator_access,
    get_current_user_id,
    get_series_credentials,
    get_series_repository,
    member_access,
    verified_google_emails,
)
from src.presentation.schemas.series import ClaimRequest, SeriesSettingsRequest

router = APIRouter(prefix="/series", tags=["series"])
calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("")
async def list_series(
    repository: SeriesRepositoryImpl = Depends(get_series_repository),
) -> dict[str, list[SeriesSummary]]:
    """List the caller's shared series."""
    return {"series": await SeriesUseCases(repository).list_for_caller()}


@calendar_router.get("/recurring-events")
async def calendar_choices(
    google_integration_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: SeriesRepositoryImpl = Depends(get_series_repository),
    credentials: SeriesCredentials = Depends(get_series_credentials),
) -> dict[str, list[CalendarEventChoice]]:
    """Offer live events from the explicitly selected personal calendar."""
    use_cases = CalendarUseCases(repository, credentials, SeriesCalendarMirror.create())
    return {"events": await use_cases.choices(user_id, google_integration_id)}


@router.post("")
async def claim_series(
    request: ClaimRequest,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    emails: frozenset[str] = Depends(verified_google_emails),
    repository: SeriesRepositoryImpl = Depends(get_series_repository),
    credentials: SeriesCredentials = Depends(get_series_credentials),
) -> dict[str, str | SeriesDetail]:
    """Claim a new series or join through the creator's trusted calendar."""
    outcome, series_id = await CalendarUseCases(repository, credentials, SeriesCalendarMirror.create()).claim(
        user_id,
        request.google_integration_id,
        request.calendar_event_id,
        emails,
    )
    access = await member_access(series_id, user_id, repository)
    response.status_code = 201 if outcome == "created" else 200
    return {"outcome": outcome, "series": await SeriesUseCases(repository).detail(access)}


@router.get("/{series_id}")
async def get_series(
    access: MemberAccess = Depends(member_access), repository: SeriesRepositoryImpl = Depends(get_series_repository)
) -> SeriesDetail:
    """Read shared settings, attendees and occurrences."""
    return await SeriesUseCases(repository).detail(access)


@router.put("/{series_id}/settings")
async def save_settings(
    request: SeriesSettingsRequest,
    access: CreatorAccess = Depends(creator_access),
    repository: SeriesRepositoryImpl = Depends(get_series_repository),
    credentials: SeriesCredentials = Depends(get_series_credentials),
) -> SeriesDetail:
    """Save creator settings and validated Slack selections."""
    return await SeriesUseCases(repository).settings(
        access,
        SeriesSettings(request.description, request.minutes_count, request.slack_message_days),
        credentials,
        request.slack.integration_id if request.slack else None,
        request.slack.channel_ids if request.slack else [],
    )


@router.post("/{series_id}/calendar-sync")
async def sync_calendar(
    access: CreatorAccess = Depends(creator_access), repository: SeriesRepositoryImpl = Depends(get_series_repository)
) -> SeriesDetail:
    """Refresh calendar state without changing creator-owned settings."""
    series = await repository.get(access.series_id)
    if series is None:
        raise SeriesError(404, "Series not found")
    await SeriesCalendarMirror.create().refresh(series)
    return await SeriesUseCases(repository).detail(access)


@router.delete("/{series_id}", status_code=204)
async def delete_series(
    access: CreatorAccess = Depends(creator_access), repository: SeriesRepositoryImpl = Depends(get_series_repository)
) -> None:
    """Delete the creator's entire shared series."""
    await repository.delete(access)
