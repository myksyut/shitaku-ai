from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from slack_sdk.errors import SlackApiError, SlackClientError

from src.application.use_cases.agenda_use_cases import GenerateAgenda
from src.config import settings
from src.domain.entities.agenda import Agenda
from src.domain.entities.google_integration import GoogleIntegration
from src.domain.entities.series import (
    CalendarErrorCode,
    CalendarSnapshot,
    CreatorAccess,
    Occurrence,
    SeriesError,
    SlackChannelRef,
    SlackErrorCode,
)
from src.domain.repositories.google_integration_repository import GoogleIntegrationRepository
from src.domain.repositories.slack_integration_repository import SlackIntegrationRepository
from src.infrastructure.external.encryption import encrypt_google_token
from src.infrastructure.external.google_calendar_client import GoogleCalendarClient
from src.infrastructure.external.google_oauth_client import GoogleOAuthClient, GoogleTokenRefreshError
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import CredentialUnavailableError, GoogleApis, SeriesCredentials
from tests.application.use_cases.test_series_use_cases import make_series


def calendar_http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://calendar.test/events")
    return httpx.HTTPStatusError(
        "Unstable provider prose", request=request, response=httpx.Response(status, request=request)
    )


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (CredentialUnavailableError("not_connected"), "not_connected"),
        (CredentialUnavailableError("scope_missing"), "scope_missing"),
        (CredentialUnavailableError("revoked"), "revoked"),
        (CredentialUnavailableError("calendar_unavailable"), "calendar_unavailable"),
        (calendar_http_error(401), "revoked"),
        (calendar_http_error(403), "scope_missing"),
        (calendar_http_error(404), "event_not_found"),
        (calendar_http_error(410), "event_not_found"),
        (calendar_http_error(429), "calendar_unavailable"),
        (calendar_http_error(503), "calendar_unavailable"),
        (httpx.ConnectError("Unstable network prose"), "calendar_unavailable"),
        (ValueError("Unstable parsing prose"), "calendar_unavailable"),
        (SeriesError(409, "Unstable source prose"), "calendar_unavailable"),
    ],
)
async def test_calendar_refresh_persists_only_stable_codes(failure: Exception, expected: CalendarErrorCode) -> None:
    series = make_series(uuid4(), uuid4())
    client = MagicMock()
    credentials = AsyncMock(spec=SeriesCredentials)
    calendar = AsyncMock(spec=GoogleCalendarClient)
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    if isinstance(failure, CredentialUnavailableError):
        credentials.google_for_series.side_effect = failure
    else:
        calendar.snapshot.side_effect = failure
    assert await SeriesCalendarMirror(client, credentials).refresh(series) == expected
    client.table.return_value.update.assert_called_once_with({"calendar_sync_error": expected})
    client.table.return_value.update.return_value.eq.assert_called_once_with("id", str(series.id))


@pytest.mark.parametrize("missing", [True, False])
async def test_missing_or_replaced_calendar_event_emits_event_not_found(missing: bool) -> None:
    client, credentials, calendar = MagicMock(), AsyncMock(), AsyncMock()
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    calendar.snapshot.return_value = (
        None
        if missing
        else CalendarSnapshot(
            "different-uid",
            "event",
            "Other",
            None,
            (),
            False,
            (),
            datetime.now(UTC) - timedelta(days=35),
            datetime.now(UTC) + timedelta(days=35),
        )
    )
    assert await SeriesCalendarMirror(client, credentials).refresh(make_series(uuid4(), uuid4())) == "event_not_found"
    client.rpc.assert_called_once()


@pytest.mark.parametrize("omitted", [True, False])
async def test_calendar_success_emits_only_omitted_warning_or_none(omitted: bool) -> None:
    client, credentials, calendar = MagicMock(), AsyncMock(), AsyncMock()
    credentials.google_for_series.return_value = GoogleApis(calendar, MagicMock(), MagicMock())
    calendar.snapshot.return_value = CalendarSnapshot(
        "uid",
        "event",
        "Weekly",
        None,
        (),
        omitted,
        (),
        datetime.now(UTC) - timedelta(days=35),
        datetime.now(UTC) + timedelta(days=35),
    )
    assert await SeriesCalendarMirror(client, credentials).refresh(make_series(uuid4(), uuid4())) == (
        "attendees_omitted" if omitted else None
    )
    client.rpc.assert_called_once()
    client.table.assert_not_called()


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("not_connected", "not_connected"),
        ("scope_missing", "scope_missing"),
        ("invalid_ciphertext", "revoked"),
        ("missing_configuration", "calendar_unavailable"),
        ("invalid_grant", "revoked"),
        ("invalid_token", "revoked"),
        ("temporarily_unavailable", "calendar_unavailable"),
        ("network", "calendar_unavailable"),
    ],
)
async def test_google_credentials_classify_missing_revoked_and_unavailable(
    case: str,
    expected: CalendarErrorCode,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "local-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "local-secret")
    uid, iid = uuid4(), uuid4()
    integration = GoogleIntegration(
        iid,
        uid,
        "owner@example.com",
        encrypt_google_token("refresh"),
        ["https://www.googleapis.com/auth/calendar.readonly"],
        datetime.now(UTC),
        None,
    )
    google, slack = AsyncMock(spec=GoogleIntegrationRepository), AsyncMock(spec=SlackIntegrationRepository)
    google.get_by_id.return_value = integration
    if case == "not_connected":
        google.get_by_id.return_value = None
    elif case == "scope_missing":
        integration.granted_scopes = []
    elif case == "invalid_ciphertext":
        integration.encrypted_refresh_token = "invalid-ciphertext"
    elif case == "missing_configuration":
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    failure = httpx.ConnectError("Unstable network prose") if case == "network" else GoogleTokenRefreshError(case)
    with (
        patch(
            "src.infrastructure.external.series_credentials.GoogleOAuthClient.refresh_access_token",
            new=AsyncMock(side_effect=failure),
        ),
        pytest.raises(CredentialUnavailableError) as error,
    ):
        await SeriesCredentials(google, slack).google_for_user(uid, iid, "calendar")
    assert error.value.code == expected and error.value.detail == expected


async def test_google_oauth_preserves_machine_readable_refresh_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "local-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "local-secret")
    response = httpx.Response(400, json={"error": "invalid_grant", "error_description": "Unstable provider prose"})
    with (
        patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)),
        pytest.raises(GoogleTokenRefreshError) as error,
    ):
        await GoogleOAuthClient().refresh_access_token("refresh")
    assert error.value.code == "invalid_grant"


async def generate_with_slack_failure(failure: Exception, *, credential_failure: bool = False) -> SlackErrorCode | None:
    sid, owner, now = uuid4(), uuid4(), datetime.now(UTC)
    stored = replace(
        make_series(sid, owner), slack_integration_id=uuid4(), slack_channels=(SlackChannelRef("chosen", "Selected"),)
    )
    target = Occurrence(uuid4(), sid, now, now, False, None, 0, None, 0, False)
    series, content, memory, knowledge, dictionary, credentials, mirror, writer = (AsyncMock() for _ in range(8))
    series.get.return_value = stored
    series.occurrences.return_value = [target]
    memory.list_items.return_value = []
    knowledge.for_occurrences.return_value = []
    dictionary.list_entries.return_value = []
    content.topics.return_value = []
    mirror.refresh.return_value = None
    writer.propose.return_value = None
    if credential_failure:
        credentials.slack_for_series.side_effect = failure
    else:
        slack = MagicMock()
        slack.get_messages.side_effect = failure
        credentials.slack_for_series.return_value = slack

    async def save(access: CreatorAccess, oid: UUID, text: str) -> Agenda:
        return Agenda(oid, sid, text, now, now)

    content.save_generated.side_effect = save
    result = await GenerateAgenda(series, content, memory, knowledge, dictionary, credentials, mirror, writer).execute(
        CreatorAccess(sid, owner), target.id
    )
    assert result.sources.slack_messages == 0
    return result.sources.slack_error


@pytest.mark.parametrize(
    ("provider_code", "expected"),
    [
        ("invalid_auth", "not_connected"),
        ("not_authed", "not_connected"),
        ("token_revoked", "not_connected"),
        ("account_inactive", "not_connected"),
        ("not_in_channel", "not_in_channel"),
        ("channel_not_found", "not_in_channel"),
        ("ratelimited", "rate_limited"),
        ("internal_error", "slack_unavailable"),
        (None, "slack_unavailable"),
    ],
)
async def test_agenda_slack_errors_are_stable_codes(provider_code: str | None, expected: SlackErrorCode) -> None:
    response = MagicMock()
    response.get.return_value = provider_code
    failure = SlackApiError("Unstable provider prose", response)  # type: ignore[no-untyped-call]
    assert await generate_with_slack_failure(failure) == expected


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (CredentialUnavailableError("not_connected"), "not_connected"),
        (CredentialUnavailableError("calendar_unavailable"), "slack_unavailable"),
        (SeriesError(409, "Unstable credential prose"), "slack_unavailable"),
        (SlackClientError("Unstable network prose"), "slack_unavailable"),
    ],
)
async def test_agenda_slack_unavailable_sources_never_expose_prose(
    failure: Exception, expected: SlackErrorCode
) -> None:
    assert await generate_with_slack_failure(failure, credential_failure=True) == expected
