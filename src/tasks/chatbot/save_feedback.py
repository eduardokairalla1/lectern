"""
Upserts visitor feedback for an exchange.
"""

# --- IMPORTS ---
from src.services.chatbot.stats.persist import upsert_feedback
from src.tasks.chatbot.config import RETRY_OPTIONS
from src.tasks.runner import run_async
from src.worker import celery_app

import logging
import uuid


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def _save_feedback(
    exchange_id: str,
    rating: str,
    comment: str | None = None
) -> None:
    """
    Upserts visitor feedback for an exchange.

    :param exchange_id: UUID (string) of the rated exchange.
    :param rating: Visitor rating: 'up' or 'down'.
    :param comment: Optional free-text comment.

    :returns: None.
    """
    # run the upsert
    try:
        await upsert_feedback(
            exchange_id=uuid.UUID(exchange_id),
            rating=rating,
            comment=comment,
        )

    # persistence failed: log which exchange it was and let Celery retry
    except Exception as e:
        logger.error(
            f'[Task] Failed to save feedback. '
            f'Exchange: {exchange_id}, Rating: {rating}, Error: {str(e)}'
        )
        raise


@celery_app.task(name='chatbot.save_feedback', **RETRY_OPTIONS)
def save_feedback(
    exchange_id: str,
    rating: str,
    comment: str | None = None
) -> None:
    """
    Upserts visitor feedback for an exchange.

    :param exchange_id: UUID (string) of the rated exchange.
    :param rating: Visitor rating: 'up' or 'down'.
    :param comment: Optional free-text comment.

    :returns: None.
    """
    run_async(_save_feedback(exchange_id, rating, comment))
