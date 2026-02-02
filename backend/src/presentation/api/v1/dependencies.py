"""API dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from src.infrastructure.external.supabase_client import (
    create_user_supabase_client,
    verify_supabase_jwt,
)

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
