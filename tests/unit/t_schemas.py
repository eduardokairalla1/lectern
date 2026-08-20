"""
Unit tests for request schemas / validators.
"""

# --- IMPORTS ---
from src.config import config
from src.dependencies.identifiers import valid_exchange_id
from src.dependencies.identifiers import valid_session_id
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.schemas.endpoints.chatbot_response import Message
from typing import Any
from typing import cast

import logging
import pytest


class _FakeSession:
    """Minimal AsyncSession stand-in: records rollback/close, touches no DB."""

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _FakeSessionMaker:

    def __call__(self) -> _FakeSession:
        return _FakeSession()
# --- MESSAGE: content ---
def test_text_message_valid() -> None:
    message = Message(content='Oi, tudo bem?', messageType='text')
    assert message.content == 'Oi, tudo bem?'
    assert message.audioBase64 is None


def test_content_at_300_chars_is_accepted() -> None:
    Message(content='a' * 300, messageType='text')


def test_content_over_300_chars_is_rejected() -> None:
    with pytest.raises(InvalidRequestError):
        Message(content='a' * 301, messageType='text')


def test_empty_text_message_is_rejected() -> None:
    # a text message with nothing to answer must not reach the LLM.
    with pytest.raises(InvalidRequestError):
        Message(content='', messageType='text')


def test_whitespace_only_text_message_is_rejected() -> None:
    with pytest.raises(InvalidRequestError):
        Message(content='   \n\t ', messageType='text')


# --- MESSAGE: messageType ---
def test_unsupported_message_type_is_rejected() -> None:
    with pytest.raises(InvalidRequestError):
        Message(content='oi', messageType='video')


def test_audio_message_with_base64_is_accepted() -> None:
    message = Message(
        content='', messageType='audio', audioBase64='ZmFrZSBhdWRpbw=='
    )
    assert message.messageType == 'audio'


def test_audio_message_without_base64_is_rejected() -> None:
    with pytest.raises(InvalidRequestError):
        Message(content='', messageType='audio', audioBase64=None)


def test_audio_base64_over_limit_is_rejected_as_too_large() -> None:
    with pytest.raises(PayloadTooLargeError):
        Message(
            content='',
            messageType='audio',
            audioBase64='a' * (config.MAX_AUDIO_BASE64_SIZE + 1),
        )


def test_audio_base64_at_limit_is_accepted() -> None:
    Message(
        content='',
        messageType='audio',
        audioBase64='a' * config.MAX_AUDIO_BASE64_SIZE,
    )


# --- CHATBOT ROUTER: sessionId ---
def _payload(session_id: str) -> dict:
    return {
        'sessionId': session_id,
        'message': {'content': 'oi tudo bem', 'messageType': 'text'},
    }


def test_session_id_valid_charset() -> None:
    router = ChatbotPayload(**_payload('abc-DEF_0123'))
    assert router.sessionId == 'abc-DEF_0123'


def test_session_id_minimum_length_boundary() -> None:
    ChatbotPayload(**_payload('a' * 10))
    with pytest.raises(InvalidRequestError):
        ChatbotPayload(**_payload('a' * 9))


def test_session_id_maximum_length_boundary() -> None:
    ChatbotPayload(**_payload('a' * 50))
    with pytest.raises(InvalidRequestError):
        ChatbotPayload(**_payload('a' * 51))


@pytest.mark.parametrize(
    'bad_session',
    [
        'has spaces in it',
        'special!chars#',
        'memory:inject',  # ':' could collide with the Redis key namespace
        'ação-sessão-12',
    ],
)
def test_session_id_invalid_characters_are_rejected(bad_session: str) -> None:
    with pytest.raises(InvalidRequestError):
        ChatbotPayload(**_payload(bad_session))

# --- FEEDBACK ROUTER ---

def test_exchange_id_path_validator_rejects_a_non_uuid() -> None:
    with pytest.raises(InvalidRequestError):
        valid_exchange_id('not-a-uuid')


def test_session_id_path_validator_rejects_an_invalid_charset() -> None:
    with pytest.raises(InvalidRequestError):
        valid_session_id('bad id!')

# --- REPOSITORY ERROR MAPPING ---
@pytest.mark.anyio
async def test_constraint_violation_is_not_reported_as_unavailable() -> None:
    """A rejected row means the database answered, so it must not be typed as
    an outage: that label would make the worker retry a write that can never
    succeed."""
    from sqlalchemy.exc import IntegrityError
    from src.databases.relational.setup.base_repository import BaseRepository
    from src.errors.data_integrity_error import DataIntegrityError

    repository = BaseRepository.__new__(BaseRepository)
    repository._session_maker = cast(Any, _FakeSessionMaker())
    repository._logger = logging.getLogger('test')

    with pytest.raises(DataIntegrityError):
        async with repository._session():
            raise IntegrityError('INSERT ...', {}, Exception('violates check'))


@pytest.mark.anyio
async def test_unexpected_database_error_is_reported_as_unavailable() -> None:
    from src.databases.relational.setup.base_repository import BaseRepository
    from src.errors.database_unavailable_error import DatabaseUnavailableError

    repository = BaseRepository.__new__(BaseRepository)
    repository._session_maker = cast(Any, _FakeSessionMaker())
    repository._logger = logging.getLogger('test')

    with pytest.raises(DatabaseUnavailableError):
        async with repository._session():
            raise ConnectionError('server closed the connection')
