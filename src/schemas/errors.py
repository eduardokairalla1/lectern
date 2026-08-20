"""
Error response schemas.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import Field
from src.errors.backend_error import BackendError
from typing import Any


# --- CODE ---
class ErrorResponse(BaseModel):
    """
    Envelope returned for every handled failure.
    """
    error: str = Field(
        description='Stable, machine-readable slug identifying the failure. '
                    'Branch on this, never on the message.',
        examples=['invalid_request_error'],
    )
    message: str = Field(
        description='Human-readable summary. Internal details are logged '
                    'server-side and never exposed here.',
        examples=['Bad Request!'],
    )


class ValidationErrorResponse(BaseModel):
    """
    Envelope returned when the request body does not match the schema.
    """
    error: str = Field(
        description="Always 'request_validation_error'.",
        examples=['request_validation_error'],
    )
    message: list[str] = Field(
        description='One entry per invalid field, as "field: reason".',
        examples=[['message -> content: Field required']],
    )


# initialize validation response dict
VALIDATION_RESPONSE: dict[int | str, dict[str, Any]] = {
    422: {
        'model': ValidationErrorResponse,
        'description': 'The body does not match the schema (missing or '
                       'wrongly typed fields).',
    }
}


def error_responses(
    *errors: type[BackendError],
) -> dict[int | str, dict[str, Any]]:
    """
    Builds OpenAPI response entries for the given error types.

    :param errors: The BackendError subclasses the route can raise.

    :return: Mapping of status code to its OpenAPI response entry.
    """
    # group by status code: distinct errors can share one (e.g. 503)
    grouped: dict[int, list[type[BackendError]]] = {}
    for error in errors:
        grouped.setdefault(error.STATUS_CODE, []).append(error)

    # describe each status by the slugs that can produce it
    return {
        status: {
            'model': ErrorResponse,
            'description': ' / '.join(
                f'`{error.slug()}` — {error.MESSAGE}' for error in group
            ),
        }
        for status, group in grouped.items()
    }
