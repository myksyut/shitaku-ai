"""Supabase client module for authentication and database operations."""

import jwt
from jwt import PyJWKClient
from supabase import Client, create_client

from src.config import settings

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


def get_supabase_client() -> Client | None:
    """Initialize and return a Supabase client with service key.

    Uses the service key (secret key) which bypasses RLS.
    Authorization is handled at the application layer.

    Returns:
        Supabase Client instance if credentials are configured, None otherwise.
    """
    if settings.SUPABASE_URL is None:
        return None

    # Prefer service key (bypasses RLS), fall back to publishable key
    key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
    if key is None:
        return None

    return create_client(settings.SUPABASE_URL, key)


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


def is_supabase_configured() -> bool:
    """Check if Supabase credentials are configured.

    Returns:
        True if SUPABASE_URL and SUPABASE_KEY are set, False otherwise.
    """
    return settings.SUPABASE_URL is not None and settings.SUPABASE_KEY is not None
