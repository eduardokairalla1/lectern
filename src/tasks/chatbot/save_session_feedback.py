"""
Upserts a visitor's rating of a whole conversation.
"""

# --- IMPORTS ---
from src.services.chatbot.stats.persist import upsert_session_feedback
from src.tasks.chatbot.config import RETRY_OPTIONS
from src.tasks.runner import run_async
from src.worker import celery_app

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def _save_session_feedback(
    session_id: str,
    score: int,
    comment: str | None = None
) -> None:
    """
    Upserts a visitor's rating of a conversation.

    :param session_id: Client session identifier.
    :param score: Visitor rating of the conversation, from 0 to 10.
    :param comment: Optional free-text note.

    :returns: None.
    """
    # run the upsert
    try:
        await upsert_session_feedback(
            session_id=session_id,
            score=score,
            comment=comment,
        )

    # persistence failed: log which session it was and let Celery retry
    except Exception as e:
        logger.error(
            f'[Task] Failed to save session feedback. '
            f'Session: {session_id}, Score: {score}, Error: {str(e)}'
        )
        raise


@celery_app.task(name='chatbot.save_session_feedback', **RETRY_OPTIONS)
def save_session_feedback(
    session_id: str,
    score: int,
    comment: str | None = None
) -> None:
    """
    Upserts a visitor's rating of a whole conversation.

    :param session_id: Client session identifier.
    :param score: Visitor rating of the conversation, from 0 to 10.
    :param comment: Optional free-text note.

    :returns: None.
    """
    run_async(_save_session_feedback(session_id, score, comment))
