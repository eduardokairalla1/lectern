"""
Base Backend error.
"""

# --- IMPORTS ---
from typing import Any

import logging
import re


# --- ERROR CLASS ---
class BackendError(Exception):
    """
    Base Backend error.

    Subclasses declare how they surface over HTTP by overriding:
    - MESSAGE: safe, user-facing message returned to the client.
    - STATUS_CODE: HTTP status code of the error response.
    - LOG_LEVEL: level used when the error handler logs the failure.

    The stable 'error' slug returned to clients is derived from the class
    name (e.g. DatabaseUnavailableError -> database_unavailable_error).
    """

    MESSAGE = 'Generic Backend error'
    STATUS_CODE = 500
    LOG_LEVEL = logging.ERROR

    def __init__(self, *args: Any) -> None:
        """
        Initialize a Backend error.

        :param *args: Optional additional context or details for the error.

        :returns: None.
        """
        super().__init__(self.MESSAGE, *args)

    @classmethod
    def slug(cls) -> str:
        """
        Stable snake_case error slug derived from the class name.
        """
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
