"""
Persists exchange and execution statistics through the repositories.
"""

# --- IMPORTS ---
from src.resources import get_resources
from src.types.stats import SessionStats

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


