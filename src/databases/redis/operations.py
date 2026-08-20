"""
Redis operations.
"""

# --- IMPORTS ---
from src.errors.redis_unavailable_error import RedisUnavailableError
from src.resources import get_resources

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def set(key: str, value: str, ttl: int | None = None) -> None:
    """
    Saves a string value in Redis with an optional expiration time.
    """
    # set key-value pair
    try:
        await get_resources().redis_client.set(name=key, value=value, ex=ttl)
        logger.debug('Set Redis key: %s (ttl=%s)', key, ttl)

    # errors occurred: raise RedisUnavailableError with details
    except Exception as e:
        raise RedisUnavailableError(
            {'operation': 'set', 'key': key, 'ttl': str(ttl), 'error': str(e)}
        ) from e

