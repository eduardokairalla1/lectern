"""
Persists exchange and execution statistics through the repositories.
"""

# --- IMPORTS ---
from src.databases.relational.models.exchanges import Exchanges
from src.databases.relational.models.executions import Executions
from src.resources import get_resources
from src.types.stats import ExchangeStats
from src.types.stats import ExecutionStats
from src.types.stats import SessionStats
from uuid import UUID

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def upsert_session(session_data: SessionStats) -> None:
    """
    Inserts or refreshes a visitor session (last_seen, metadata and counter).

    :param session_data: Dictionary with session fields (id, request_ip,
        user_agent).

    :returns: None.
    """
    await get_resources().sessions_repository.upsert_session(
        session_id=session_data['id'],
        request_ip=session_data.get('request_ip'),
        user_agent=session_data.get('user_agent'),
    )
    logger.debug(
        f'[Insert Stats] Session upserted. ID: {session_data["id"]}'
    )


async def upsert_feedback(
    exchange_id: UUID,
    rating: str,
    comment: str | None = None
) -> None:
    """
    Inserts or updates the visitor feedback of an exchange.

    :param exchange_id: UUID of the rated exchange.
    :param rating: Visitor rating: 'up' or 'down'.
    :param comment: Optional free-text comment.

    :returns: None.
    """
    await get_resources().exchange_feedback_repository.upsert_feedback(
        exchange_id=exchange_id,
        rating=rating,
        comment=comment,
    )
    logger.debug(
        f'[Insert Stats] Feedback upserted. '
        f'Exchange: {exchange_id}, Rating: {rating}'
    )


async def upsert_session_feedback(
    session_id: str,
    score: int,
    comment: str | None = None
) -> None:
    """
    Records the visitor's rating of a whole conversation, at its current
    depth.

    :param session_id: Client session identifier.
    :param score: Visitor rating of the conversation, from 0 to 10.
    :param comment: Optional free-text note.

    :returns: None.
    """
    await get_resources().session_feedback_repository.upsert_session_feedback(
        session_id=session_id,
        score=score,
        comment=comment,
    )
    logger.debug(
        f'[Insert Stats] Session feedback upserted. '
        f'Session: {session_id}, Score: {score}'
    )


async def insert_exchange(
    exchange_data: ExchangeStats,
) -> Exchanges:
    """
    Insert the exchange metrics into database.

    :param exchange_data: Dictionary with exchange fields.

    :returns: The created exchange object.
    """
    # insert exchange
    exchange = await get_resources().exchanges_repository.insert_exchange(
        Exchanges(**exchange_data)
    )
    logger.debug(
        f'[Insert Stats] Exchange saved. ID: {exchange.id}, '
        f'Session: {exchange.session_id}'
    )

    return exchange


async def insert_executions(
    exchange_id: UUID,
    executions: list[ExecutionStats],
) -> None:
    """
    Insert the execution metrics into database.

    :param exchange_id: UUID of the parent exchange.
    :param executions: Dictionaries with execution metrics.

    :returns: None.
    """
    # build executions
    executions_model = [
        Executions(exchange_id=exchange_id, **execution_data)
        for execution_data in executions
    ]

    # insert executions
    await get_resources().executions_repository.insert_executions(
        executions_model
    )
    logger.debug(
        f'[Insert Stats] Executions saved ({len(executions)}). '
        f'Exchange: {exchange_id}'
    )
