"""
Persists an exchange and its execution metrics to the database.
"""

# --- IMPORTS ---
from src.services.chatbot.stats.persist import insert_exchange
from src.services.chatbot.stats.persist import insert_executions
from src.services.chatbot.stats.persist import upsert_session
from src.tasks.chatbot.config import RETRY_OPTIONS
from src.tasks.runner import run_async
from src.types.stats import ExchangeStats
from src.types.stats import ExecutionStats
from src.types.stats import SessionStats
from src.worker import celery_app

import logging
import uuid


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def _save_exchange_stats(
    session_data: SessionStats,
    exchange_data: ExchangeStats,
    executions: list[ExecutionStats]
) -> None:
    """
    Saves an exchange and its execution metrics to the database.

    :param session_data: Serialized session fields (id, request_ip, user_agent).
    :param exchange_data: Serialized exchange fields.
    :param executions: Serialized execution metric dicts, in pipeline order.

    :returns: None.
    """
    # log the start of the task
    session_id = exchange_data.get('session_id')
    exchange_id = exchange_data.get('id')
    logger.debug(f'[Task] Saving exchange stats. Session: {session_id}')

    # upsert the session first
    try:
        await upsert_session(session_data)

        # exchange ID is a string: convert it to a UUID for persistence
        if isinstance(exchange_id, str):
            exchange_data['id'] = uuid.UUID(exchange_id)

        # save the exchange itself
        exchange = await insert_exchange(exchange_data)

        # save all executions linked to this exchange
        await insert_executions(
            exchange_id=exchange.id,
            executions=executions,
        )

    # persistence failed: log which exchange it was and let Celery retry
    except Exception as e:
        logger.error(
            f'[Task] Failed to save exchange stats. '
            f'Session: {session_id}, Exchange: {exchange_id}, '
            f'Error: {str(e)}'
        )
        raise

    # log the successful completion of the task
    logger.debug(
        f'[Task] Exchange stats saved ({len(executions)} executions). '
        f'Session: {session_id}'
    )


@celery_app.task(name='chatbot.save_exchange_stats', **RETRY_OPTIONS)
def save_exchange_stats(
    session_data: SessionStats,
    exchange_data: ExchangeStats,
    executions: list[ExecutionStats]
) -> None:
    """
    Persists an exchange and its execution metrics to the database.

    :param session_data: Serialized session fields (id, request_ip, user_agent).
    :param exchange_data: Serialized exchange fields.
    :param executions: Serialized execution metric dicts, in pipeline order.

    :returns: None.
    """
    run_async(
        _save_exchange_stats(session_data, exchange_data, executions)
    )
