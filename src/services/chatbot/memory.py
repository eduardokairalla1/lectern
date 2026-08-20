"""
Conversation summary memory.
"""

# --- IMPORTS ---

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CONSTANTS ---
TTL_SECONDS = 30 * 60
MAX_SUMMARY_CHARS = 2000
MAX_RECENT_INTERACTIONS = 2


# --- CODE ---
def _summary_key(session_id: str) -> str:
    """
    Redis key holding the conversation summary.

    :param session_id: Conversation identifier.

    :return: Redis key for the summary.
    """
    return f'memory:{session_id}'


def _recent_key(session_id: str) -> str:
    """
    Redis key holding the recent raw interactions.

    :param session_id: Conversation identifier.

    :return: Redis key for the recent interactions.
    """
    return f'memory:{session_id}:recent'


