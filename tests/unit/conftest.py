"""
Shared test fixtures.

Installs a Resources container of fakes (via src.resources.set_resources)
before the app starts, so endpoints and services run against an in-memory
Redis/Qdrant/engine: no real infrastructure needed.
"""

# --- IMPORTS ---
from collections.abc import AsyncIterator
from collections.abc import Iterator
from src.resources import Resources
from src.resources import set_resources
from typing import Any
from typing import cast

import fnmatch
import pytest


# --- ASYNC BACKEND ---
@pytest.fixture(scope='session')
def anyio_backend() -> str:
    """Run @pytest.mark.anyio tests on asyncio only (trio not installed)."""
    return 'asyncio'


# --- FAKES ---
class FakeRedis:
    """
    In-memory stand-in for redis.asyncio.Redis (decode_responses=True).

    Set `fail = True` to simulate an outage: every operation raises.
    TTLs are recorded (not enforced) so tests can assert expiration policy.
    """

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}
        self.fail = False


    def _check(self) -> None:
        if self.fail:
            raise ConnectionError('fake redis is down')


    async def ping(self) -> bool:
        self._check()
        return True


    async def aclose(self) -> None:
        return None


    async def set(
        self, name: str, value: str, ex: int | None = None
    ) -> None:
        self._check()
        self.data[name] = value
        self.ttls[name] = ex


    async def get(self, name: str) -> str | None:
        self._check()
        return self.data.get(name)


    async def delete(self, *names: str) -> None:
        self._check()
        for name in names:
            self.data.pop(name, None)
            self.ttls.pop(name, None)


    async def expire(self, name: str, ttl: int) -> None:
        self._check()
        if name in self.data:
            self.ttls[name] = ttl


    async def scan_iter(self, match: str = '*') -> AsyncIterator[str]:
        self._check()
        for key in list(self.data):
            if fnmatch.fnmatch(key, match):
                yield key


class FakeQdrant:

    def __init__(self) -> None:
        self.closed = False


    def close(self) -> None:
        self.closed = True


class FakeEngine:

    def __init__(self) -> None:
        self.disposed = False


    async def dispose(self) -> None:
        self.disposed = True


# --- RESOURCES ---
def make_fake_resources(fake_redis: FakeRedis | None = None) -> Resources:
    """Builds a Resources container entirely backed by fakes."""
    return Resources(
        vector_client=cast(Any, FakeQdrant()),
        redis_client=cast(Any, fake_redis or FakeRedis()),
        database_engine=cast(Any, FakeEngine()),
        exchanges_repository=cast(Any, None),
        executions_repository=cast(Any, None),
        sessions_repository=cast(Any, None),
        exchange_feedback_repository=cast(Any, None),
        session_feedback_repository=cast(Any, None),
    )


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def resources(fake_redis: FakeRedis) -> Iterator[Resources]:
    """Installs a fresh container of fakes for the duration of the test."""
    container = make_fake_resources(fake_redis)
    set_resources(container)
    yield container
    set_resources(None)

