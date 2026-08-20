"""
Unsupported message type error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError

import logging


# --- ERROR ---
class UnsupportedMessageTypeError(BackendError):
    """
    Raised when no resolver is registered for the message's type.
    """

    MESSAGE = 'Unsupported message type!'
    STATUS_CODE = 500
    LOG_LEVEL = logging.ERROR
