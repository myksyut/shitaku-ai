from typing import cast
from unittest.mock import MagicMock

from src.infrastructure.external.supabase_client import ServiceClient, UserClient


def as_user_client(client: MagicMock) -> UserClient:
    return cast(UserClient, client)


def as_service_client(client: MagicMock) -> ServiceClient:
    return cast(ServiceClient, client)
