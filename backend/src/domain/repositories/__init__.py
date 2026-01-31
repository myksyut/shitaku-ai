"""Domain repositories module.

This module exports repository interfaces that define the contract
for persistence operations. Implementations are in the infrastructure layer.
"""

from src.domain.repositories.user_repository import UserRepository

__all__ = ["UserRepository"]
