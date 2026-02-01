"""Google OAuth client for token exchange and API access.

Handles OAuth 2.0 Authorization Code Flow with Incremental Authorization support.
Following ADR-0003 authentication pattern.
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from src.config import settings

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Default scopes for initial OAuth
DEFAULT_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# Additional scopes for transcript access (Incremental Authorization)
TRANSCRIPT_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


@dataclass
class GoogleTokenResponse:
    """Google OAuth token response."""

    access_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str
    scope: str


@dataclass
class GoogleUserInfo:
    """Google user profile information."""

    email: str
    name: str | None
    picture: str | None


class GoogleOAuthClient:
    """Google OAuth client for authentication and token management."""

    def __init__(self) -> None:
        """Initialize the Google OAuth client."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth is not configured")

        self._client_id = settings.GOOGLE_CLIENT_ID
        self._client_secret = settings.GOOGLE_CLIENT_SECRET
        self._redirect_uri = settings.GOOGLE_REDIRECT_URI

    def get_authorization_url(
        self,
        state: str,
        scopes: list[str] | None = None,
        include_granted_scopes: bool = True,
    ) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            state: CSRF protection state token.
            scopes: OAuth scopes to request. Defaults to DEFAULT_SCOPES.
            include_granted_scopes: If True, retain previously granted scopes
                (Incremental Authorization).

        Returns:
            The authorization URL to redirect the user to.
        """
        if scopes is None:
            scopes = DEFAULT_SCOPES

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent screen for refresh token
        }

        if include_granted_scopes:
            params["include_granted_scopes"] = "true"

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: The authorization code from OAuth callback.

        Returns:
            GoogleTokenResponse with access and refresh tokens.

        Raises:
            ValueError: If token exchange fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise ValueError(f"Google OAuth token exchange failed: {error_msg}")

            data = response.json()
            return GoogleTokenResponse(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_in=data["expires_in"],
                token_type=data["token_type"],
                scope=data.get("scope", ""),
            )

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token to use.

        Returns:
            GoogleTokenResponse with new access token.

        Raises:
            ValueError: If token refresh fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise ValueError(f"Google OAuth token refresh failed: {error_msg}")

            data = response.json()
            return GoogleTokenResponse(
                access_token=data["access_token"],
                refresh_token=refresh_token,  # Refresh token is not returned on refresh
                expires_in=data["expires_in"],
                token_type=data["token_type"],
                scope=data.get("scope", ""),
            )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user profile information from Google.

        Args:
            access_token: A valid Google access token.

        Returns:
            GoogleUserInfo with user's email and profile.

        Raises:
            ValueError: If user info retrieval fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise ValueError("Failed to get Google user info")

            data = response.json()
            return GoogleUserInfo(
                email=data["email"],
                name=data.get("name"),
                picture=data.get("picture"),
            )

    @staticmethod
    def parse_scopes(scope_string: str) -> list[str]:
        """Parse scope string into list of scopes.

        Args:
            scope_string: Space-separated scope string.

        Returns:
            List of individual scopes.
        """
        return scope_string.split() if scope_string else []
