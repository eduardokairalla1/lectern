"""
Schemas for POST /api/chatbot/feedback/session/{sessionId}.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from src.errors.invalid_request_error import InvalidRequestError

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

MIN_SESSION_SCORE = 0
MAX_SESSION_SCORE = 10
MAX_SESSION_COMMENT_LENGTH = 1000


# --- PAYLOADS ---
class SessionFeedbackPayload(BaseModel):
    """
    A visitor's rating of a whole conversation. The session is in the path.
    """
    score: int = Field(
        description=f'Rating of the conversation, from '
                    f'{MIN_SESSION_SCORE} to {MAX_SESSION_SCORE}.',
        examples=[9],
    )
    comment: str | None = Field(
        default=None,
        description='Optional free-text note, up to '
                    f'{MAX_SESSION_COMMENT_LENGTH} characters.',
        examples=['Achei o que eu precisava rápido.'],
    )

    @field_validator('score')
    @classmethod
    def score_validator(cls, score: int) -> int:
        """"
        Validate that the score is within the allowed range.

        :param score: The score to validate.

        :raise InvalidRequestError: If the score is out of range.

        :return: The validated score.
        """
        # score is out of range: log a warning and raise an error
        if not MIN_SESSION_SCORE <= score <= MAX_SESSION_SCORE:
            logger.warning(
                f'Validation failed: score out of range. '
                f'Received: {score}, '
                f'Range: {MIN_SESSION_SCORE}-{MAX_SESSION_SCORE}'
            )
            raise InvalidRequestError()

        return score

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
        if comment is not None and len(comment) > MAX_SESSION_COMMENT_LENGTH:
            logger.warning(
                f'Validation failed: Session feedback comment too long. '
                f'Length: {len(comment)}, '
                f'Max: {MAX_SESSION_COMMENT_LENGTH}'
            )
            raise InvalidRequestError()

        return comment
