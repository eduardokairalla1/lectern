"""
Invalid request error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError

import logging


# --- ERROR ---
class InvalidRequestError(BackendError):
    """
    Raised when the request payload is malformed or fails validation.
    """

    MESSAGE = 'Bad Request!'
    STATUS_CODE = 400
    LOG_LEVEL = logging.WARNING
