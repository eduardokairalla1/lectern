"""
HTTP exception handlers.
"""

# --- IMPORTS ---
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.errors.backend_error import BackendError
from starlette.exceptions import HTTPException

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
def _details(error: BackendError) -> object:
    """
    Extracts the optional details payload passed at raise time.

    :param error: The raised error.

    :return: The details payload, or None when none was given.
    """
    return error.args[1] if len(error.args) > 1 else None


def _route_of(request: Request) -> tuple[str, str]:
    """
    Extracts the method and path being handled, for logging.

    :param request: The incoming request.

    :return: Tuple of (method, path).
    """
    return request.scope['method'], request.scope['path']


async def backend_error_handler(
    request: Request,
    error: BackendError,
) -> JSONResponse:
    """
    Handles any BackendError, and every subclass of it.

    :param request: The incoming request.
    :param error: The raised error.

    :return: JSON response shaped by the error class itself.
    """
    # log at the level the class declares, with its internal details
    logger.log(
        error.LOG_LEVEL, '%s: %s', type(error).__name__, _details(error)
    )

    # answer with the safe, client-facing envelope
    return JSONResponse(
        {'error': error.slug(), 'message': error.MESSAGE},
        status_code=error.STATUS_CODE,
    )


async def http_exception_handler(
    request: Request,
    error: HTTPException,
) -> JSONResponse:
    """
    Handles HTTPException, including the 404/405 raised by the router.

    :param request: The incoming request.
    :param error: The raised exception.

    :return: JSON response carrying the exception's status and detail.
    """
    # log the route that failed
    method, path = _route_of(request)
    logger.error(
        'Request "%s %s" failed with %s: %s',
        method,
        path,
        error.status_code,
        error.detail,
    )

    return JSONResponse(
        {'error': 'http_error', 'message': error.detail},
        status_code=error.status_code,
    )


async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """
    Handles a body that does not match the schema.

    :param request: The incoming request.
    :param error: The validation error raised by FastAPI.

    :return: JSON response listing one entry per invalid field.
    """
    # build one 'field: reason' entry per invalid field
    errors = []
    for err in error.errors():
        path = ' -> '.join(map(str, err['loc'][1:]))
        errors.append(f'{path}: {err["msg"]}')

    # log the route that failed
    method, path = _route_of(request)
    logger.error(
        'Validation for "%s %s" failed: %s', method, path, '; '.join(errors)
    )

    return JSONResponse(
        {'error': 'request_validation_error', 'message': errors},
        status_code=422,
    )


async def unhandled_error_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    """
    Handles anything that is not a BackendError.

    :param request: The incoming request.
    :param error: The unhandled exception.

    :return: JSON response with a generic 500.
    """
    # log the route that failed
    method, path = _route_of(request)
    logger.error(
        'Request "%s %s" failed with an unhandled error',
        method,
        path,
        exc_info=error,
    )

    return JSONResponse(
        {'error': 'processing_error', 'message': 'Internal Server Error!'},
        status_code=500,
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Registers every exception handler on the application.

    :param app: The FastAPI application instance.

    :return: None.
    """
    app.add_exception_handler(BackendError, backend_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, unhandled_error_handler)
