from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import httpx
from cryptography.fernet import InvalidToken

from src.domain.entities.series import Series, SeriesError
from src.domain.repositories.google_integration_repository import GoogleIntegrationRepository
from src.domain.repositories.slack_integration_repository import SlackIntegrationRepository
from src.infrastructure.external.encryption import decrypt_google_token, decrypt_token, encrypt_google_token
from src.infrastructure.external.google_calendar_client import GoogleCalendarClient
from src.infrastructure.external.google_docs_client import GoogleDocsClient
from src.infrastructure.external.google_drive_client import GoogleDriveClient
from src.infrastructure.external.google_oauth_client import GoogleOAuthClient
from src.infrastructure.external.slack_client import SlackClient


class CredentialUnavailableError(SeriesError):
    """A selected integration cannot supply the required API."""

    def __init__(self, reason: str) -> None:
        super().__init__(409, reason)


@dataclass(frozen=True, slots=True)
class GoogleApis:
    """API clients, never raw credentials."""

    calendar: GoogleCalendarClient
    drive: GoogleDriveClient
    docs: GoogleDocsClient


class SeriesCredentials:
    """Decrypt and refresh only explicitly selected, owner-scoped integrations."""

    def __init__(self, google: GoogleIntegrationRepository, slack: SlackIntegrationRepository) -> None:
        self._google = google
        self._slack = slack

    async def google_for_user(
        self, user_id: UUID, integration_id: UUID, need: Literal["calendar", "drive"]
    ) -> GoogleApis:
        """Open the caller's selected integration."""
        integration = await self._google.get_by_id(integration_id, user_id)
        if integration is None:
            raise CredentialUnavailableError("Google integration not connected")
        scopes = (
            {"https://www.googleapis.com/auth/calendar.readonly"}
            if need == "calendar"
            else {
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/documents.readonly",
            }
        )
        if not scopes.issubset(integration.granted_scopes):
            raise CredentialUnavailableError("Google scope missing")
        try:
            token = await GoogleOAuthClient().refresh_access_token(
                decrypt_google_token(integration.encrypted_refresh_token)
            )
        except (ValueError, InvalidToken, httpx.HTTPError) as error:
            raise CredentialUnavailableError("Google credentials unavailable") from error
        if token.refresh_token and decrypt_google_token(integration.encrypted_refresh_token) != token.refresh_token:
            integration.update_token(encrypt_google_token(token.refresh_token))
            await self._google.update(integration)
        return GoogleApis(
            GoogleCalendarClient(token.access_token),
            GoogleDriveClient(token.access_token),
            GoogleDocsClient(token.access_token),
        )

    async def google_for_series(self, series: Series, need: Literal["calendar", "drive"]) -> GoogleApis:
        """Open only the creator's bound integration."""
        if series.google_integration_id is None:
            raise CredentialUnavailableError("Google integration not connected")
        return await self.google_for_user(series.created_by, series.google_integration_id, need)

    async def slack_for_user(self, user_id: UUID, integration_id: UUID) -> SlackClient:
        """Open a selected personal Slack integration."""
        integration = await self._slack.get_by_id(integration_id, user_id)
        if integration is None:
            raise CredentialUnavailableError("Slack integration not connected")
        try:
            return SlackClient(decrypt_token(integration.encrypted_access_token))
        except (ValueError, InvalidToken) as error:
            raise CredentialUnavailableError("Slack credentials unavailable") from error

    async def slack_for_series(self, series: Series) -> SlackClient | None:
        """Open the creator's bound Slack source, if selected."""
        if series.slack_integration_id is None:
            return None
        return await self.slack_for_user(series.created_by, series.slack_integration_id)
