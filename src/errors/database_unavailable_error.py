"""
Database unavailable error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class DatabaseUnavailableError(BackendError):
    """
    Raised when the database is unavailable or a database operation fails.
    """

    MESSAGE = 'Database unavailable'
    STATUS_CODE = 503
