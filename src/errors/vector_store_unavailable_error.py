"""
Vector store unavailable error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class VectorStoreUnavailableError(BackendError):
    """
    Raised when the vector store is unreachable.
    """

    MESSAGE = 'Service Temporarily Unavailable!'
    STATUS_CODE = 502
