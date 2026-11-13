import asyncio
import sys
from pathlib import Path

from mypy import api as mypy_api

CLIENT_IMPORTS = """
from typing import assert_type
from supabase import Client
from src.infrastructure.external.supabase_client import (
    UserClient, ServiceClient, create_user_supabase_client, get_supabase_client,
)
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import SeriesCredentials
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.infrastructure.repositories.google_integration_repository_impl import GoogleIntegrationRepositoryImpl
from src.infrastructure.repositories.knowledge_repository_impl import KnowledgeRepositoryImpl
from src.infrastructure.repositories.oauth_state_repository_impl import OAuthStateRepositoryImpl
from src.infrastructure.repositories.occurrence_repository_impl import OccurrenceRepositoryImpl
from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.infrastructure.repositories.slack_integration_repository_impl import SlackIntegrationRepositoryImpl
from src.infrastructure.repositories.team_memory_repository_impl import TeamMemoryRepositoryImpl
"""
VALID_CLIENT_USAGE = (
    CLIENT_IMPORTS
    + """
def valid(user: UserClient, service: ServiceClient, credentials: SeriesCredentials) -> None:
    DictionaryRepositoryImpl(user)
    KnowledgeRepositoryImpl(user)
    OccurrenceRepositoryImpl(user)
    SeriesRepositoryImpl(user)
    TeamMemoryRepositoryImpl(user)
    SeriesCalendarMirror(service, credentials)
    GoogleIntegrationRepositoryImpl(user)
    GoogleIntegrationRepositoryImpl(service)
    SlackIntegrationRepositoryImpl(user)
    SlackIntegrationRepositoryImpl(service)
    OAuthStateRepositoryImpl(user)
    OAuthStateRepositoryImpl(service)
    assert_type(create_user_supabase_client('token'), UserClient | None)
    assert_type(get_supabase_client(), ServiceClient | None)
"""
)
INVALID_CLIENT_USAGE = (
    CLIENT_IMPORTS
    + """
def invalid(user: UserClient, service: ServiceClient, raw: Client, credentials: SeriesCredentials) -> None:
    DictionaryRepositoryImpl(service)
    KnowledgeRepositoryImpl(service)
    OccurrenceRepositoryImpl(service)
    SeriesRepositoryImpl(service)
    TeamMemoryRepositoryImpl(service)
    SeriesCalendarMirror(user, credentials)
    SeriesRepositoryImpl(raw)
    user = service
"""
)


async def test_mypy_and_ty_reject_mixed_client_roles(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    for name, code, expected_success in (("valid", VALID_CLIENT_USAGE, True), ("invalid", INVALID_CLIENT_USAGE, False)):
        source = tmp_path / f"{name}_clients.py"
        source.write_text(code)
        stdout, stderr, status = mypy_api.run(["--config-file", str(root / "pyproject.toml"), str(source)])
        assert (status == 0) == expected_success, stdout + stderr
        if not expected_success:
            assert "UserClient" in stdout and "ServiceClient" in stdout and "[arg-type]" in stdout
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "ty",
            "check",
            "--project",
            str(root),
            str(source),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=root,
        )
        output, errors = await process.communicate()
        diagnostics = (output + errors).decode()
        assert (process.returncode == 0) == expected_success, diagnostics
        if not expected_success:
            assert (
                "invalid-argument-type" in diagnostics
                and "UserClient" in diagnostics
                and "ServiceClient" in diagnostics
            )
