"""
Data integrity error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR CLASS ---
class DataIntegrityError(BackendError):
    """
    A write violated a database constraint.

    Distinct from DatabaseUnavailableError on purpose: the database answered,
    and it rejected the data. Retrying sends the same rejected row again, so
    the background tasks exclude this one from their retry policy.
    """

    MESSAGE = 'Conflicting Data!'
    STATUS_CODE = 409
