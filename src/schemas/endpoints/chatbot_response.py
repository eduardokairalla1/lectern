"""
Schemas for POST /api/chatbot/response and /api/chatbot/response/stream.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError

import logging
import re


# --- GLOBALS ---
logger = logging.getLogger(__name__)

MESSAGE_SUPPORTED_TYPES = ['text', 'audio']
SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{10,50}$')


# --- PAYLOADS ---
class Message(BaseModel):
    """
    The visitor's message, as text or as recorded audio.
    """
    content: str = Field(
        description='Question text, up to 300 characters. Send an empty '
                    "string when messageType is 'audio' — the transcription "
                    'replaces it.',
        examples=['What projects has the subject worked on?'],
    )
    audioBase64: str | None = Field(
        default=None,
        description='Base64 of the recorded audio, required when '
                    "messageType is 'audio' and rejected otherwise. Up to "
                    '10MB of base64 (~7.5MB of audio). Accepted containers: '
                    f'{", ".join(config.AUDIO_SUPPORTED_FORMATS)}.',
        examples=[None],
    )
    messageType: str = Field(
        description=f'One of: {", ".join(MESSAGE_SUPPORTED_TYPES)}.',
        examples=['text'],
    )


    @field_validator('content')
    @classmethod
    def message_validator(cls, content: str) -> str:
        """
        Validate that the message content is not too long.

        :param content: The message content to validate.

        :raise InvalidRequestError: If the content is too long.

        :return: The validated content.
        """
        # content is too long: log a warning and raise an error
        if len(content) > 300:
            logger.warning(
                f'Validation failed: Message content too long. '
                f'Length: {len(content)}, Max: 300'
            )
            raise InvalidRequestError()

        return content


    @field_validator('messageType')
    @classmethod
    def message_type_validator(cls, messageType: str) -> str:
        """
        Validate that the message type is supported.

        :param messageType: The message type to validate.

        :raise InvalidRequestError: If the message type is unsupported.

        :return: The validated message type.
        """
        # message type is unsupported: log a warning and raise an error
        if messageType not in MESSAGE_SUPPORTED_TYPES:
            logger.warning(
                f'Validation failed: Unsupported message type. '
                f"Received: '{messageType}', "
                f'Supported: {MESSAGE_SUPPORTED_TYPES}'
            )
            raise InvalidRequestError()

        return messageType


    @model_validator(mode='after')
    def validate_audio_requirements(self) -> 'Message':
        """
        Validate that the audio requirements are met based on the message type.

        :raise InvalidRequestError: If the audio requirements are not met.
        :raise PayloadTooLargeError: If the audio base64 is too large.

        :return: The validated Message instance.
        """
        # messageType is 'text': content must not be empty
        if self.messageType == 'text' and not self.content.strip():
            logger.warning(
                'Validation failed: empty content for text message'
            )
            raise InvalidRequestError()

        # messageType is 'audio': audioBase64 must be present and within
        # size limits
        if self.messageType == 'audio':

            # audioBase64 is missing: log a warning and raise an error
            if not self.audioBase64:
                logger.warning(
                    'Validation failed: audioBase64 is missing for audio '
                    'message type'
                )
                raise InvalidRequestError()

            # audioBase64 is too large: log a warning and raise an error
            if len(self.audioBase64) > config.MAX_AUDIO_BASE64_SIZE:
                max_mb = config.MAX_AUDIO_BASE64_SIZE / (1024 * 1024)
                actual_mb = len(self.audioBase64) / (1024 * 1024)
                logger.warning(
                    f'Validation failed: Audio base64 too large. '
                    f'Size: {actual_mb:.2f}MB, Max: {max_mb:.1f}MB'
                )
                raise PayloadTooLargeError()

        return self


class ChatbotPayload(BaseModel):
    """
    A question, tied to a conversation by its sessionId.
    """
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'sessionId': 'a1b2c3d4e5f6',
                    'message': {
                        'content': 'What projects has the subject worked on?',
                        'messageType': 'text',
                        'audioBase64': None,
                    },
                }
            ]
        }
    }

    sessionId: str = Field(
        description='Conversation identifier generated by the client: 10-50 '
                    'characters of letters, digits, hyphen or underscore. '
                    'Reuse it across messages so the assistant keeps the '
                    'conversation context; start a new one for a new '
                    'conversation.',
        examples=['a1b2c3d4e5f6'],
    )
    message: Message

    @field_validator('sessionId')
    @classmethod
    def session_id_validator(cls, sessionId: str) -> str:
        """
        Validate the session ID.

        :param sessionId: The session ID to validate.

        :raise InvalidRequestError: If the session ID is invalid.

        :return: The validated session ID.
        """
        # sessionId is invalid: log a warning and raise an error
        if not SESSION_ID_PATTERN.fullmatch(sessionId):
            logger.warning(
                'Validation failed: Invalid sessionId. Length: %s, '
                'must be 10-50 chars of [A-Za-z0-9_-]',
                len(sessionId),
            )
            raise InvalidRequestError()

        return sessionId


# --- RESPONSES ---
class ChatbotResponse(BaseModel):
    """
    Assistant answer returned by POST /api/chatbot/response.
    """
    response: str = Field(
        description="The assistant's answer, in the visitor's language.",
        examples=['They built, among other things, an API that...'],
    )
    exchangeId: str | None = Field(
        default=None,
        description='UUID identifying this question/answer pair, to be '
                    'sent to POST '
                    '/api/chatbot/feedback/exchange/{exchangeId}.',
        examples=['3f2504e0-4f89-11d3-9a0c-0305e82c3301'],
    )
