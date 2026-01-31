"""User repository interface for domain layer.

Abstract base class defining the contract for user persistence operations.
Implementations should be provided in the infrastructure layer.
"""

from abc import ABC, abstractmethod

from src.domain.entities.user import User


class UserRepository(ABC):
    """Abstract repository interface for User entity.

    This interface follows the Repository pattern from DDD,
    defining the contract for user persistence operations.
    Concrete implementations are provided in the infrastructure layer.
    """

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Retrieve a user by their unique identifier.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            The User entity if found, None otherwise.
        """

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by their email address.

        Args:
            email: The email address of the user.

        Returns:
            The User entity if found, None otherwise.
        """

    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user in the repository.

        Args:
            user: The User entity to create.

        Returns:
            The created User entity with assigned ID.
        """

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user in the repository.

        Args:
            user: The User entity with updated values.

        Returns:
            The updated User entity.

        Raises:
            ValueError: If the user does not exist.
        """

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete a user from the repository.

        Args:
            user_id: The unique identifier of the user to delete.

        Returns:
            True if the user was deleted, False if not found.
        """

    @abstractmethod
    def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Retrieve all users with pagination.

        Args:
            skip: Number of users to skip (offset).
            limit: Maximum number of users to return.

        Returns:
            A list of User entities.
        """
