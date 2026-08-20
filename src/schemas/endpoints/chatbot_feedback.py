"""
Schemas for POST /api/chatbot/feedback/exchange/{exchangeId}.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from src.errors.invalid_request_error import InvalidRequestError

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

FEEDBACK_RATINGS = ['up', 'down']
MAX_FEEDBACK_COMMENT_LENGTH = 500


# --- PAYLOADS ---
class FeedbackPayload(BaseModel):
    """
    A visitor's rating of one answer. The exchange is in the path.
    """
    rating: str = Field(
        description=f'One of: {", ".join(FEEDBACK_RATINGS)}.',
        examples=['up'],
    )
    comment: str | None = Field(
        default=None,
        description='Optional free-text note, up to '
                    f'{MAX_FEEDBACK_COMMENT_LENGTH} characters.',
        examples=['Resposta clara e direta.'],
    )

    @field_validator('rating')
    @classmethod
    def rating_validator(cls, rating: str) -> str:
        """
        Validate that the rating is one of the supported values.

        :param rating: The rating to validate.

        :raise InvalidRequestError: If the rating is unsupported.

        :return: The validated rating.
        """
        # rating is unsupported: log a warning and raise an error
        if rating not in FEEDBACK_RATINGS:
            logger.warning(
                f'Validation failed: Unsupported rating. '
                f"Received: '{rating}', Supported: {FEEDBACK_RATINGS}"
            )
            raise InvalidRequestError()

        return rating


    @field_validator('comment')
    @classmethod
    def comment_validator(cls, comment: str | None) -> str | None:
        """
        Validate that the comment is not too long.

        :param comment: The comment to validate.

        :raise InvalidRequestError: If the comment is too long.

        :return: The validated comment.
        """
        # comment is too long: log a warning and raise an error
        if comment is not None and len(comment) > MAX_FEEDBACK_COMMENT_LENGTH:
            logger.warning(
                f'Validation failed: Feedback comment too long. '
                f'Length: {len(comment)}, '
                f'Max: {MAX_FEEDBACK_COMMENT_LENGTH}'
            )
            raise InvalidRequestError()

        return comment


# --- RESPONSES ---
class FeedbackResponse(BaseModel):
    """
    Acknowledgement returned by both feedback endpoints.

    The feedback is persisted by a background task, so the endpoint only
    confirms that it was accepted.
    """
    status: str = Field(
        description="Always 'accepted'.",
        examples=['accepted'],
    )
