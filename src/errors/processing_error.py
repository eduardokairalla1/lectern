"""
Processing error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class ProcessingError(BackendError):
    """
    Raised when the assistant pipeline fails to process a request.
    """

    MESSAGE = 'Internal Server Error!'
