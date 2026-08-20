"""
API key authentication dependency.
"""

# --- IMPORTS ---
from fastapi import Security
from fastapi.security import APIKeyHeader
from src.config import config
from src.errors.unauthorized_error import UnauthorizedError
from typing import Annotated

import logging
import secrets


# --- GLOBALS ---
logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(
    name='x-api-key',
    auto_error=False,
    description='Shared API key issued to clients of this instance.',
)


# --- CODE ---
async def verify_api_key(
    x_api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> None:
    """
    Validates the request's API key against the configured one.

    :param x_api_key: API key provided in the X-API-Key header.

    :raises UnauthorizedError: If the key is missing or does not match.
    """
    # missing or non-matching API key: log and raise an UnauthorizedError
    if not x_api_key or not secrets.compare_digest(x_api_key, config.API_KEY):
        logger.warning('Unauthorized API access attempt')
        raise UnauthorizedError()
