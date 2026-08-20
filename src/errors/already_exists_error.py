"""
Already Exists error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class AlreadyExistsError(BackendError):
    """
    Raised when trying to create an entity that already exists.
    """

    MESSAGE = 'Entity already exists'
    STATUS_CODE = 409
