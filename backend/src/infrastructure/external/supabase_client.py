"""Supabase client module for authentication and database operations."""

import logging
from typing import NewType

import jwt
from jwt import PyJWKClient
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from src.config import settings

UserClient = NewType("UserClient", Client)
ServiceClient = NewType("ServiceClient", Client)

logger = logging.getLogger(__name__)

# JWKS client (lazy initialization)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient | None:
    """Get or create JWKS client for JWT verification.

    Returns:
        PyJWKClient instance if SUPABASE_URL is configured, None otherwise.
    """
    global _jwks_client

    if settings.SUPABASE_URL is None:
        return None

    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)

    return _jwks_client


def get_supabase_client() -> ServiceClient | None:
    """Initialize and return a Supabase client with service key.

    Uses the service key (secret key) which bypasses RLS.
    Authorization is handled at the application layer.

    Returns:
        Supabase Client instance if credentials are configured, None otherwise.
    """
    if settings.SUPABASE_URL is None:
        return None

    key = settings.SUPABASE_SERVICE_KEY
    if key is None:
        return None

    return ServiceClient(create_client(settings.SUPABASE_URL, key))


def verify_supabase_jwt(token: str) -> dict[str, object] | None:
    """Verify a Supabase JWT token using JWKS and return the decoded payload.

    Uses asymmetric key verification via the JWKS endpoint.
    Supports RS256 and ES256 algorithms.

    Args:
        token: JWT token string to verify.

    Returns:
        Decoded JWT payload as a dictionary if valid, None otherwise.
    """
    jwks_client = _get_jwks_client()
    if jwks_client is None:
        return None

    try:
        # Get signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Verify and decode (issuer not checked for local dev compatibility)
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_iss": False},
        )
        return dict(decoded)
    except jwt.PyJWTError as e:
        import logging

        logging.error(f"JWT verification failed: {e}")
        return None


def create_user_supabase_client(access_token: str) -> UserClient | None:
    """Create a Supabase client with user context for RLS enforcement.

    This client uses the user's JWT token in the Authorization header,
    allowing RLS policies to identify the user via auth.uid().

    Args:
        access_token: User's JWT access token from Supabase Auth.

    Returns:
        Supabase Client with user context if configured, None otherwise.
    """
    if settings.SUPABASE_URL is None or settings.SUPABASE_KEY is None:
        return None

    if not access_token:
        logger.warning("Empty access token provided to create_user_supabase_client")
        return None

    # Use anon key with user's JWT for RLS enforcement
    options = SyncClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
    )

    return UserClient(
        create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
            options=options,
        )
    )
