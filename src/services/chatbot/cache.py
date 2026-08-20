"""
Response cache.
"""

# --- IMPORTS ---
from src.databases.redis import operations
from src.errors.redis_unavailable_error import RedisUnavailableError
from src.services.chatbot.types import CachedResponse

import hashlib
import json
import logging
import string


# --- GLOBALS ---
logger = logging.getLogger(__name__)

CACHE_PREFIX = 'response_cache:'
CACHE_TTL_SECONDS = 3600  # 1 hour


# --- CODE ---
def _cache_key(query: str) -> str:
    """
    Builds a cache key from a user query (normalized then hashed).

    :param query: Original user query.

    :return: Cache key string.
    """
    # get the normalized query
    tokens = query.lower().split()

    # normalize the tokens and hash the normalized query
    stripped = [t.strip(string.punctuation + '¿¡"\'') for t in tokens]
    normalized = ' '.join(t for t in stripped if t)
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]

    # build the cache key with the prefix and the digest
    return f'{CACHE_PREFIX}{digest}'


async def get_cached_response(query: str) -> CachedResponse | None:
    """
    Returns the cached response for a query, or None on miss/error.

    :param query: User query.

    :return: Cached response or None.
    """
    # get the cached response from Redis
    try:
        cached = await operations.get(_cache_key(query))

        # cache hit: parse the cached JSON and return it
        if cached:
            logger.debug('[Cache] HIT (query %s chars)', len(query))
            return json.loads(cached)

        # cache miss: return None
        logger.debug('[Cache] MISS (query %s chars)', len(query))
        return None

    # Redis is unavailable: log a warning and return None
    except RedisUnavailableError as e:
        logger.warning('[Cache] Error getting cache: %s', e.args)
        return None


async def set_cached_response(
    query: str,
    response: str,
    answered: bool,
    category: str,
    ttl: int = CACHE_TTL_SECONDS,
) -> bool:
    """
    Caches a successful response. Unanswered responses are not cached.

    :param query: User query.
    :param response: Assistant response text.
    :param answered: Whether the question was answered.
    :param category: Response category.
    :param ttl: Time-to-live in seconds.

    :return: True if cached successfully, False otherwise.
    """
    # question was not answered: skip caching and return False
    if not answered:
        logger.debug('[Cache] Skipping unanswered question')
        return False

    # cache the response in Redis
    try:
        cached_response: CachedResponse = {
            'response': response,
            'answered': answered,
            'category': category,
        }
        payload = json.dumps(cached_response, ensure_ascii=False)

        # store the cached response
        await operations.set(_cache_key(query), payload, ttl)
        logger.debug('[Cache] Stored response (query %s chars)', len(query))

        # return True on success
        return True

    # Redis is unavailable: log a warning and return False
    except RedisUnavailableError as e:
        logger.warning('[Cache] Error setting cache: %s', e.args)
        return False


async def invalidate_cached_response(query: str) -> bool:
    """
    Removes a cached response for a query.

    :param query: User query.

    :return: True if invalidated successfully, False otherwise.
    """
    # delete the cached response
    try:
        await operations.delete(_cache_key(query))
        logger.debug('[Cache] Invalidated entry (query %s chars)', len(query))

        # return True on success
        return True

    # Redis is unavailable: log a warning and return False
    except RedisUnavailableError as e:
        logger.warning('[Cache] Error invalidating cache: %s', e.args)
        return False


