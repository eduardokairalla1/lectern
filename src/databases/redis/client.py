"""
Redis client factory.
"""

# --- IMPORTS ---
from redis.asyncio import Redis


# --- CODE ---
def redis_client_factory(url: str) -> Redis:
    """
    Creates an async Redis client.

    :param url: The URL of the Redis service.

    :return: An instance of the async Redis client.
    """
    return Redis.from_url(url=url, decode_responses=True)
