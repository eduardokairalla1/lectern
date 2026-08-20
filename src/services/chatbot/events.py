"""
Server-Sent Events (SSE) for the chatbot.
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError
from src.services.chatbot.types import StreamErrorCode
from src.services.chatbot.types import StreamEvent

import asyncio
import html
import json
import openai
import re


# --- META-ARTIFACT STRIPPING ---
# Safety net: the assistant must never write internal fields in its reply
# (enforced in the system prompt), but if a leak like a trailing
# "answered = true" / "category: ..." / "Justification: ..." ever slips through
# the streamed text, we strip it before the response is stored or cached so it
# can't be persisted and re-served to other users.
_META_TAIL = re.compile(
    r'\s*(?:'
    r'answered\s*[:=]\s*(?:true|false)'
    r'|category\s*[:=].*'
    r'|reasoning\s*[:=].*'
    r'|justification\s*:.*'
    r')\s*$',
    re.IGNORECASE,
)


def strip_meta_artifacts(text: str) -> str:
    """
    Remove trailing internal-metadata lines the model may have accidentally
    appended to its reply (answered/category/reasoning/justification).

    :param text: Raw response text.
    :return: Text with trailing metadata artifacts removed.
    """
    if not text:
        return text

    previous = None
    while previous != text:
        previous = text
        text = _META_TAIL.sub('', text)

    return text.rstrip()


# --- OUTPUT SANITIZATION ---
def sanitize_output(text: str) -> str:
    """
    Sanitize LLM output to prevent XSS attacks.
    Escapes HTML special characters while preserving markdown.

    :param text: Raw text from LLM.
    :return: Sanitized text safe for SSE transmission.
    """
    if not text:
        return text

    # Escape HTML entities to prevent XSS.
    # This preserves markdown syntax but escapes <script>, <img onerror>, etc.
    sanitized = html.escape(text, quote=False)

    return sanitized


# --- EVENT CONSTRUCTORS ---
def token_event(content: str) -> StreamEvent:
    """A chunk of assistant text."""
    return {'type': 'token', 'content': content}


def stream_end_event() -> StreamEvent:
    """Streaming of tokens is done (UI can hide the cursor)."""
    return {'type': 'stream_end'}


def done_event(
    answered: bool, category: str, exchange_id: str | None = None
) -> StreamEvent:
    """Terminal event carrying the final answered/category metadata.

    `exchangeId` (additive field) lets the client reference this exchange
    later (e.g. feedback); absent on cache hits, which don't create an
    exchange row.
    """
    event: StreamEvent = {
        'type': 'done', 'answered': answered, 'category': category
    }
    if exchange_id:
        event['exchangeId'] = exchange_id
    return event


def ready_event(session_id: str) -> StreamEvent:
    """Emitted first so the client can confirm the session is being
    processed."""
    return {'type': 'ready', 'sessionId': session_id}


def error_event(error_code: StreamErrorCode, message: str) -> StreamEvent:
    """A recoverable/terminal error. `error_code` lets the client localize."""
    return {'type': 'error', 'error_code': error_code, 'message': message}


# --- SERIALIZATION ---
def format_sse(event: StreamEvent) -> str:
    """Serialize an event dict into a Server-Sent Events frame."""
    return f'data: {json.dumps(event)}\n\n'


# --- ERROR CLASSIFICATION ---
# Ordered lookup table: the FIRST matching exception type wins, so more
# specific types must come before their base classes (e.g. APITimeoutError
# and RateLimitError before APIError). BackendError covers step-level
# failures (e.g. vector store/DB).
_STREAM_ERROR_TABLE: tuple[
    tuple[tuple[type[BaseException], ...], tuple[StreamErrorCode, str]], ...
] = (
    (
        (asyncio.TimeoutError, openai.APITimeoutError),
        ('timeout', 'The response took too long. Please try again.'),
    ),
    (
        (openai.RateLimitError,),
        (
            'rate_limit',
            "I'm receiving a lot of requests right now. "
            'Please try again in a moment.',
        ),
    ),
    (
        (openai.AuthenticationError,),
        (
            'auth',
            'The assistant is temporarily unavailable. Please try again later.',
        ),
    ),
    (
        (openai.APIConnectionError, openai.APIError),
        (
            'unavailable',
            'The assistant is temporarily unavailable. '
            'Please try again shortly.',
        ),
    ),
    (
        (BackendError,),
        (
            'unavailable',
            'The assistant is temporarily unavailable. '
            'Please try again shortly.',
        ),
    ),
)
_UNKNOWN_STREAM_ERROR: tuple[StreamErrorCode, str] = (
    'unknown',
    'Something went wrong while processing your request. Please try again.',
)


def classify_stream_error(
    exc: Exception,
) -> tuple[StreamErrorCode, str]:
    """Map an exception to a stable (error_code, user-facing message).

    The message is a neutral English default; the client should localize
    based on `error_code`. Never leak internal details to the user.
    """
    return next(
        (
            result
            for exc_types, result in _STREAM_ERROR_TABLE
            if isinstance(exc, exc_types)
        ),
        _UNKNOWN_STREAM_ERROR,
    )
