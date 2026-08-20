"""
Shared configuration for the chatbot tasks.
"""

# --- IMPORTS ---
from src.errors.data_integrity_error import DataIntegrityError
from typing import Any


# --- GLOBALS ---
RETRY_OPTIONS: dict[str, Any] = {
    'autoretry_for': (Exception,),
    'dont_autoretry_for': (DataIntegrityError,),
    'retry_backoff': True,
    'retry_backoff_max': 60,
    'retry_jitter': True,
    'retry_kwargs': {'max_retries': 3},
}
