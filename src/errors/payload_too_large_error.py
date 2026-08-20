"""
Payload too large error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError

import logging


# --- ERROR ---
class PayloadTooLargeError(BackendError):
    """
    Raised when the request payload exceeds the allowed size (e.g. audio).
    """

    MESSAGE = 'Payload Too Large!'
    STATUS_CODE = 413
    LOG_LEVEL = logging.WARNING
