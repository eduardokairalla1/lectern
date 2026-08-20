"""
Response cache.
"""

# --- IMPORTS ---

import hashlib
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


