"""Token encryption module using Fernet (AES-128-CBC with HMAC).

Provides secure encryption and decryption for OAuth access tokens.
Supports both Slack and Google OAuth tokens with separate encryption keys.
"""

from cryptography.fernet import Fernet

from src.config import settings


def get_encryption_key() -> bytes:
    """Get encryption key from settings.

    Returns:
        Encryption key as bytes.

    Raises:
        ValueError: If SLACK_TOKEN_ENCRYPTION_KEY is not set.
    """
    key = settings.SLACK_TOKEN_ENCRYPTION_KEY
    if not key:
        raise ValueError("SLACK_TOKEN_ENCRYPTION_KEY is not set")
    return key.encode()


def encrypt_token(token: str) -> str:
    """Encrypt an OAuth access token.

    Args:
        token: Plain text token to encrypt.

    Returns:
        Encrypted token as base64-encoded string.
    """
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted OAuth access token.

    Args:
        encrypted_token: Encrypted token (base64-encoded).

    Returns:
        Decrypted plain text token.
    """
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Use this for initial setup to create SLACK_TOKEN_ENCRYPTION_KEY
    or GOOGLE_TOKEN_ENCRYPTION_KEY.

    Returns:
        New Fernet key as string.
    """
    return Fernet.generate_key().decode()


# Google OAuth Token Encryption
# -----------------------------


def get_google_encryption_key() -> bytes:
    """Get Google encryption key from settings.

    Returns:
        Encryption key as bytes.

    Raises:
        ValueError: If GOOGLE_TOKEN_ENCRYPTION_KEY is not set.
    """
    key = settings.GOOGLE_TOKEN_ENCRYPTION_KEY
    if not key:
        raise ValueError("GOOGLE_TOKEN_ENCRYPTION_KEY is not set")
    return key.encode()


def encrypt_google_token(token: str) -> str:
    """Encrypt a Google OAuth refresh token.

    Args:
        token: Plain text token to encrypt.

    Returns:
        Encrypted token as base64-encoded string.
    """
    fernet = Fernet(get_google_encryption_key())
    return fernet.encrypt(token.encode()).decode()


def decrypt_google_token(encrypted_token: str) -> str:
    """Decrypt an encrypted Google OAuth refresh token.

    Args:
        encrypted_token: Encrypted token (base64-encoded).

    Returns:
        Decrypted plain text token.
    """
    fernet = Fernet(get_google_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()
