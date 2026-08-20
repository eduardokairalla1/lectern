"""
Unsupported media type error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError

import logging


# --- ERROR ---
class UnsupportedMediaTypeError(BackendError):
    """
    Raised when the provided media format is not supported (e.g. audio codec).
    """

    MESSAGE = 'Unsupported Media Type!'
    STATUS_CODE = 415
    LOG_LEVEL = logging.WARNING
