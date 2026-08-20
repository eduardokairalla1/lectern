"""
Base relational repository.
"""

# --- IMPORTS ---
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.errors.backend_error import BackendError
from src.errors.data_integrity_error import DataIntegrityError
from src.errors.database_unavailable_error import DatabaseUnavailableError


# --- CODE ---
class BaseRepository:
    """
    Base class shared by every relational repository.
    """

    def __init__(self, engine: AsyncEngine, logger: Logger) -> None:
        """
        Initializes the repository.

        :param engine: SQLAlchemy async engine.
        :param logger: The logger instance for logging database operations.

        :returns: None.
        """
        # build the session factory once, it only depends on the engine
        self._session_maker: async_sessionmaker[AsyncSession] = (
            async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        )
        self._logger = logger


    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Opens a database session for a single repository operation.

        :raises DataIntegrityError: If the write violates a constraint.
        :raises DatabaseUnavailableError: If the operation fails for any
            other reason than an already-typed BackendError.

        :returns: Async generator yielding the active session.
        """
        # open a new session
        session = self._session_maker()

        try:
            yield session

        # error already carries its HTTP contract: roll back and re-raise
        except BackendError:
            await session.rollback()
            raise

        # the database answered and rejected the data: that is a bug or
        # bad input, not an outage, and retrying replays the same rejection
        except IntegrityError as e:
            await session.rollback()
            self._logger.error('Database integrity violation: %s', str(e))
            raise DataIntegrityError({'error': str(e)}) from e

        # database is unavailable: roll back, log and raise error
        except Exception as e:
            await session.rollback()
            self._logger.error('Database operation failed: %s', str(e))
            raise DatabaseUnavailableError({'error': str(e)}) from e

        # no matter what: close session
        finally:
            await session.close()
