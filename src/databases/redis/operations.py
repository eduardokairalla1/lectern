"""
Redis operations.
"""

# --- IMPORTS ---
from src.errors.redis_unavailable_error import RedisUnavailableError
from src.resources import get_resources
from typing import cast

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


async def get(key: str) -> str | None:
    """
    Retrieves a string value from Redis by its key.

    :param key: The key of the value to retrieve.

    :return: The string value associated with the key, or None if not found.
    """
    # get value by key
    try:
        result = await get_resources().redis_client.get(name=key)
        logger.debug('Got Redis key: %s', key)

        # return the result, cast to str | None
        return cast('str | None', result)

    # errors occurred: raise RedisUnavailableError with details
    except Exception as e:
        raise RedisUnavailableError(
            {'operation': 'get', 'key': key, 'error': str(e)}
        ) from e

