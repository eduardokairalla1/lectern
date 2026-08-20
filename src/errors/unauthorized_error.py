"""
Unauthorized error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError

import logging


# --- ERROR ---
class UnauthorizedError(BackendError):
    """
    Raised when a request fails authentication (e.g. invalid API key).
    """

    MESSAGE = 'Unauthorized!'
    STATUS_CODE = 401
    LOG_LEVEL = logging.WARNING
