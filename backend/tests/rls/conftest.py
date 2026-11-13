import subprocess
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from secrets import token_urlsafe
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client

from src.config import settings
from src.infrastructure.external.supabase_client import create_user_supabase_client


@dataclass(frozen=True)
class RlsUser:
    id: UUID
    email: str
    access_token: str
    client: Client


class RlsEnvironment(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RLS_", case_sensitive=True)

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    DB_URL: str = ""


@pytest.fixture(scope="session", autouse=True)
def rls_env() -> Iterator[RlsEnvironment]:
    environment = RlsEnvironment()
    if not (environment.SUPABASE_URL and environment.SUPABASE_ANON_KEY and environment.SUPABASE_SERVICE_KEY):
        pytest.skip("local Supabase not configured; run make test-rls")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "SUPABASE_URL", environment.SUPABASE_URL)
        patch.setattr(settings, "SUPABASE_KEY", environment.SUPABASE_ANON_KEY)
        patch.setattr(settings, "SUPABASE_SERVICE_KEY", environment.SUPABASE_SERVICE_KEY)
        yield environment


@pytest.fixture(scope="session")
def service_client(rls_env: RlsEnvironment) -> Client:
    return create_client(rls_env.SUPABASE_URL, rls_env.SUPABASE_SERVICE_KEY)


@pytest.fixture
def make_user(rls_env: RlsEnvironment, service_client: Client) -> Iterator[Callable[[str], RlsUser]]:
    with ExitStack() as cleanup:

        def create_user(tag: str) -> RlsUser:
            email = f"rls-{tag}-{uuid4().hex}@example.com"
            password = token_urlsafe(24)
            response = service_client.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
            assert response.user is not None, "Supabase Auth must return the newly created user"
            user_id = UUID(response.user.id)
            cleanup.callback(service_client.auth.admin.delete_user, str(user_id))

            token_response = httpx.post(
                f"{rls_env.SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={"apikey": rls_env.SUPABASE_ANON_KEY},
                json={"email": email, "password": password},
                timeout=10.0,
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            assert isinstance(access_token, str), "Supabase Auth must return a user access token"
            client = create_user_supabase_client(access_token)
            assert client is not None, "The user client must use the explicitly configured local Supabase"
            return RlsUser(id=user_id, email=email, access_token=access_token, client=client)

        yield create_user


@pytest.fixture
def creator(make_user: Callable[[str], RlsUser]) -> RlsUser:
    return make_user("creator")


@pytest.fixture
def attendee(make_user: Callable[[str], RlsUser]) -> RlsUser:
    return make_user("attendee")


@pytest.fixture
def outsider(make_user: Callable[[str], RlsUser]) -> RlsUser:
    return make_user("outsider")


@pytest.fixture
def add_identity(rls_env: RlsEnvironment) -> Callable[[RlsUser, str, bool, str], None]:
    def insert(user: RlsUser, email: str, verified: bool, provider: str = "google") -> None:
        sql = """
            insert into auth.identities
                (id, user_id, provider_id, provider, identity_data, created_at, updated_at)
            values (gen_random_uuid(), :'uid', :'uid', :'provider',
                    jsonb_build_object('sub', :'uid', 'email', :'email', 'email_verified', :'verified'::boolean),
                    now(), now())
            on conflict (provider_id, provider) do update set identity_data = excluded.identity_data;
        """
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "psql",
                rls_env.DB_URL,
                "-v",
                "ON_ERROR_STOP=1",
                "-q",
                "-v",
                f"uid={user.id}",
                "-v",
                f"provider={provider}",
                "-v",
                f"email={email}",
                "-v",
                f"verified={str(verified).lower()}",
            ],
            input=sql,
            text=True,
            capture_output=True,
            check=True,
        )

    return insert
