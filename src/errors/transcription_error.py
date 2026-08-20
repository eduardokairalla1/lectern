"""
Transcription error.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError


# --- ERROR ---
class TranscriptionError(BackendError):
    """
    Raised when audio transcription fails unexpectedly.
    """

    MESSAGE = 'Internal Server Error!'
