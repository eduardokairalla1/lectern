"""
Unit tests for how the repository layer types its failures.
"""

# --- IMPORTS ---
from typing import Any
from typing import cast

import logging
import pytest


class _FakeSession:
    """Minimal AsyncSession stand-in: records rollback/close, touches no DB."""

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _FakeSessionMaker:

    def __call__(self) -> _FakeSession:
        return _FakeSession()
# --- REPOSITORY ERROR MAPPING ---
@pytest.mark.anyio
async def test_constraint_violation_is_not_reported_as_unavailable() -> None:
    """A rejected row means the database answered, so it must not be typed as
    an outage: that label would make the worker retry a write that can never
    succeed."""
    from sqlalchemy.exc import IntegrityError
    from src.databases.relational.setup.base_repository import BaseRepository
    from src.errors.data_integrity_error import DataIntegrityError

    repository = BaseRepository.__new__(BaseRepository)
    repository._session_maker = cast(Any, _FakeSessionMaker())
    repository._logger = logging.getLogger('test')

    with pytest.raises(DataIntegrityError):
        async with repository._session():
            raise IntegrityError('INSERT ...', {}, Exception('violates check'))


@pytest.mark.anyio
async def test_unexpected_database_error_is_reported_as_unavailable() -> None:
    from src.databases.relational.setup.base_repository import BaseRepository
    from src.errors.database_unavailable_error import DatabaseUnavailableError

    repository = BaseRepository.__new__(BaseRepository)
    repository._session_maker = cast(Any, _FakeSessionMaker())
    repository._logger = logging.getLogger('test')

    with pytest.raises(DatabaseUnavailableError):
        async with repository._session():
            raise ConnectionError('server closed the connection')
