"""
Redis unavailable error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class RedisUnavailableError(BackendError):
    """
    Raised when Redis is unavailable or a Redis operation fails.
    """

    MESSAGE = 'Redis unavailable'
    STATUS_CODE = 503
