import asyncio
import threading
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import httpx

from src.infrastructure.repositories.series_repository_impl import SeriesRepositoryImpl
from src.main import create_app
from src.presentation.api.v1.dependencies import get_current_user_id, get_series_repository


async def test_blocking_series_query_does_not_block_other_requests() -> None:
    app = create_app()
    started, release = threading.Event(), threading.Event()
    worker_threads: list[int] = []
    loop_thread = threading.get_ident()
    repository = MagicMock(spec=SeriesRepositoryImpl)

    def blocking_roles() -> dict[UUID, str]:
        worker_threads.append(threading.get_ident())
        started.set()
        assert release.wait(timeout=10)
        return {}

    repository.roles.side_effect = blocking_roles
    app.dependency_overrides[get_series_repository] = lambda: repository
    app.dependency_overrides[get_current_user_id] = uuid4
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        pending = asyncio.create_task(client.get("/api/v1/series"))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            health = await asyncio.wait_for(client.get("/api/v1/health"), timeout=2)
            assert health.status_code == 200
            assert len(worker_threads) == 1
            assert worker_threads[0] != loop_thread
        finally:
            release.set()
        result = await pending
    assert result.status_code == 200 and result.json() == {"series": []}
