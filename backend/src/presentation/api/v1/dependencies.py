"""API dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from src.domain.entities.series import CreatorAccess, MemberAccess, parse_email
from src.infrastructure.external.series_credentials import SeriesCredentials
from src.infrastructure.external.supabase_client import (
    create_user_supabase_client,
    verify_supabase_jwt,
)
from src.infrastructure.repositories.google_integration_repository_impl import GoogleIntegrationRepositoryImpl
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.infrastructure.repositories.slack_integration_repository_impl import SlackIntegrationRepositoryImpl

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Verify JWT token and return the authenticated user ID.

    Args:
        credentials: HTTP Bearer credentials containing the JWT token.

    Returns:
        UUID of the authenticated user.

    Raises:
        HTTPException: 401 if token is invalid, expired, or user ID not found.
    """
    token = credentials.credentials
    payload = verify_supabase_jwt(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return UUID(str(user_id))
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


async def get_user_supabase_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Client:
    """Get a Supabase client with user context for RLS enforcement.

    This dependency creates a Supabase client that uses the user's JWT token,
    enabling RLS policies to automatically filter data by user.

    Args:
        credentials: HTTP Bearer credentials containing the JWT token.

    Returns:
        Supabase Client with user context.

    Raises:
        HTTPException: 401 if token is invalid or client creation fails.
    """
    token = credentials.credentials

    # Verify token first
    payload = verify_supabase_jwt(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create user-context client
    client = create_user_supabase_client(token)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Supabase client",
        )

    return client


def get_series_repository(client: Client = Depends(get_user_supabase_client)) -> SeriesRepositoryImpl:
    """Bind series queries to the caller's JWT."""
    return SeriesRepositoryImpl(client)


def get_series_credentials(client: Client = Depends(get_user_supabase_client)) -> SeriesCredentials:
    """Bind credential lookups to the authenticated integration owner."""
    return SeriesCredentials(GoogleIntegrationRepositoryImpl(client), SlackIntegrationRepositoryImpl(client))


async def member_access(
    series_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: SeriesRepositoryImpl = Depends(get_series_repository),
) -> MemberAccess:
    """Use the same membership function as database RLS."""
    role = (await repository.roles()).get(series_id)
    if role is None:
        raise HTTPException(404, "Series not found")
    proof = CreatorAccess if role == "creator" else MemberAccess
    return proof(series_id, user_id)


def creator_access(access: MemberAccess = Depends(member_access)) -> CreatorAccess:
    """Distinguish a member's forbidden operation from an invisible series."""
    if not isinstance(access, CreatorAccess):
        raise HTTPException(403, "Only the series creator can do this")
    return access


def verified_google_emails(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    client: Client = Depends(get_user_supabase_client),
) -> frozenset[str]:
    """Read verified identities from Auth, not mutable JWT email claims."""
    response = client.auth.get_user(credentials.credentials)
    if response is None or response.user is None:
        raise HTTPException(401, "User not found")
    emails: set[str] = set()
    for identity in response.user.identities or []:
        data = identity.identity_data or {}
        email = parse_email(data.get("email"))
        if identity.provider == "google" and data.get("email_verified") is True and email:
            emails.add(email)
    return frozenset(emails)
