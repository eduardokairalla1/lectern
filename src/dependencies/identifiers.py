"""
Path identifier validation.
"""

# --- IMPORTS ---
from fastapi import Path
from src.errors.invalid_request_error import InvalidRequestError
from typing import Annotated

import logging
import uuid


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
def valid_exchange_id(
    exchangeId: Annotated[
        str,
        Path(description='UUID of the exchange, taken from the answer that '
                         'returned it.',
             examples=['3f2504e0-4f89-11d3-9a0c-0305e82c3301']),
    ],
) -> str:
    """
    Validates the exchange identifier carried in the path.

    :param exchangeId: Identifier of the exchange being addressed.

    :raises InvalidRequestError: If it is not a valid UUID.

    :return: The validated identifier.
    """
    # not a UUID: log and raise
    try:
        uuid.UUID(exchangeId)

    except (ValueError, AttributeError, TypeError) as e:
        logger.warning('Validation failed: exchangeId is not a valid UUID')
        raise InvalidRequestError() from e

    return exchangeId
