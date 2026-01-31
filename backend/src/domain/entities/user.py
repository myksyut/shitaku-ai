"""User entity for domain layer.

Pure Python entity without SQLAlchemy/Pydantic dependencies.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """User entity representing a user in the domain.

    Attributes:
        id: Unique identifier for the user.
        email: User's email address (unique).
        hashed_password: Hashed password for authentication.
        is_active: Whether the user account is active.
        is_superuser: Whether the user has superuser privileges.
        created_at: Timestamp when the user was created.
        updated_at: Timestamp when the user was last updated.
    """

    id: int
    email: str
    hashed_password: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime | None

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True

    def grant_superuser(self) -> None:
        """Grant superuser privileges to the user."""
        self.is_superuser = True

    def revoke_superuser(self) -> None:
        """Revoke superuser privileges from the user."""
        self.is_superuser = False
