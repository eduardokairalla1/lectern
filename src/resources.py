"""
Shared runtime resources.
"""

# --- IMPORTS ---
from dataclasses import dataclass
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from src.config import config
from src.databases.redis.client import redis_client_factory
from src.databases.relational.repositories.exchange_feedback import (
    ExchangeFeedbackRepository,
)
from src.databases.relational.repositories.exchanges import ExchangesRepository
from src.databases.relational.repositories.executions import (
    ExecutionsRepository,
)
from src.databases.relational.repositories.session_feedback import (
    SessionFeedbackRepository,
)
from src.databases.relational.repositories.sessions import SessionsRepository
from src.databases.relational.setup.engine import create_database_engine
from src.databases.vector.client import vector_client_factory

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
@dataclass
class Resources:
    """
    Container for shared runtime resources.
    """
    vector_client: QdrantClient
    redis_client: Redis
    database_engine: AsyncEngine
    exchanges_repository: ExchangesRepository
    executions_repository: ExecutionsRepository
    sessions_repository: SessionsRepository
    exchange_feedback_repository: ExchangeFeedbackRepository
    session_feedback_repository: SessionFeedbackRepository


# initialize runtime resources object
_resources: Resources | None = None


def create_resources() -> Resources:
    """
    Builds a fresh Resources container from the configuration.

    :return: The initialized Resources container.
    """
    vector_client = vector_client_factory(url=config.QDRANT_URL)
    redis_client = redis_client_factory(url=config.REDIS_URL)
    database_engine = create_database_engine(config.DATABASE_URL)

    # return the Resources container
    return Resources(
        vector_client=vector_client,
        redis_client=redis_client,
        database_engine=database_engine,
        exchanges_repository=ExchangesRepository(engine=database_engine,
                                                 logger=logger),
        executions_repository=ExecutionsRepository(engine=database_engine,
                                                   logger=logger),
        sessions_repository=SessionsRepository(engine=database_engine,
                                               logger=logger),
        exchange_feedback_repository=ExchangeFeedbackRepository(
            engine=database_engine, logger=logger),
        session_feedback_repository=SessionFeedbackRepository(
            engine=database_engine, logger=logger),
    )


def get_resources() -> Resources:
    """
    Returns the process-wide Resources container, creating it if necessary.

    :return: The process-wide Resources container.
    """
    # reference the global variable
    global _resources

    # resources container is not yet created: create it
    if _resources is None:
        _resources = create_resources()

    # return the resources container
    return _resources


def set_resources(resources: Resources | None) -> None:
    """
    Replaces the process-wide resources.

    NOTE: This is intended for testing purposes only.

    :param resources: The container to install (or None to clear).

    :returns: None.
    """
    global _resources
    _resources = resources


async def close_resources() -> None:
    """
    Closes every open client, disposes the engine and clears the container.

    :returns: None.
    """
    # reference the global variable
    global _resources

    # resources container is not yet created: nothing to close
    if _resources is None:
        return

    # close every client and dispose the database engine
    await _resources.redis_client.aclose()
    _resources.vector_client.close()
    await _resources.database_engine.dispose()

    # clear the resources container
    _resources = None
