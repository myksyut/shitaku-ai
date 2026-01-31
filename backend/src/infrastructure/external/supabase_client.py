"""Supabase client module for authentication and database operations."""

import jwt
from supabase import Client, create_client

from src.config import settings


def get_supabase_client() -> Client | None:
    """Initialize and return a Supabase client.

    Returns:
        Supabase Client instance if credentials are configured, None otherwise.
    """
    if settings.SUPABASE_URL is None or settings.SUPABASE_KEY is None:
        return None

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def verify_supabase_jwt(token: str) -> dict[str, object] | None:
    """Verify a Supabase JWT token and return the decoded payload.

    Args:
        token: JWT token string to verify.

    Returns:
        Decoded JWT payload as a dictionary if valid, None otherwise.
    """
    if settings.SUPABASE_JWT_SECRET is None:
        return None

    try:
        decoded = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return dict(decoded)
    except jwt.PyJWTError:
        return None
