"""
Path identifier validation.
"""

# --- IMPORTS ---
from fastapi import Path
from src.errors.invalid_request_error import InvalidRequestError
from src.schemas.endpoints.chatbot_response import SESSION_ID_PATTERN
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


def valid_session_id(
    sessionId: Annotated[
        str,
        Path(description='Conversation identifier, the same value used for '
                         'its messages.',
             examples=['a1b2c3d4e5f6']),
    ],
) -> str:
    """
    Validates the session identifier carried in the path.

    The pattern is imported from the message payload rather than repeated:
    a second copy could drift from the one that created the session.

    :param sessionId: Identifier of the conversation being addressed.

    :raises InvalidRequestError: If it does not match the allowed charset.

    :return: The validated identifier.
    """
    # charset or length does not match: log and raise
    if not SESSION_ID_PATTERN.fullmatch(sessionId):
        logger.warning(
            'Validation failed: Invalid sessionId. Length: %s, '
            'must be 10-50 chars of [A-Za-z0-9_-]',
            len(sessionId),
        )
        raise InvalidRequestError()

    return sessionId
