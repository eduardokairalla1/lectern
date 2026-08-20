"""
Unit tests for the SSE event constructors and error classification.
"""

# --- IMPORTS ---
from src.errors.vector_store_unavailable_error import (
    VectorStoreUnavailableError,
)
from src.services.chatbot.events import classify_stream_error
from src.services.chatbot.events import done_event
from src.services.chatbot.events import error_event
from src.services.chatbot.events import format_sse
from src.services.chatbot.events import ready_event
from src.services.chatbot.events import sanitize_output
from src.services.chatbot.events import stream_end_event
from src.services.chatbot.events import strip_meta_artifacts
from src.services.chatbot.events import token_event

import httpx
import json
import openai
import pytest


# --- HELPERS ---
def _openai_error(cls: type, status: int) -> openai.APIStatusError:
    """Builds a real provider error, since the table matches on its type."""
    request = httpx.Request('POST', 'https://api.openai.com/v1/chat')
    return cls(
        'boom', response=httpx.Response(status, request=request), body=None
    )


# --- OUTPUT SANITIZATION ---
class TestSanitizeOutput:

    def test_escapes_html_special_characters(self) -> None:
        assert sanitize_output('<script>') == '&lt;script&gt;'

    def test_escapes_ampersand_but_not_quotes(self) -> None:
        # quote=False: the text lands in element content, never in an
        # attribute, and escaping quotes would disfigure ordinary prose
        assert sanitize_output('a & "b"') == 'a &amp; "b"'

    def test_preserves_markdown_emphasis(self) -> None:
        assert sanitize_output('**bold** _it_') == '**bold** _it_'

    def test_empty_string_stays_empty(self) -> None:
        assert sanitize_output('') == ''

    def test_is_idempotent_only_on_plain_text(self) -> None:
        # escaping twice would double-encode, which is why the streaming path
        # sanitizes each token exactly once
        once = sanitize_output('<b>')
        assert sanitize_output(once) != once


class TestStripMetaArtifacts:

    def test_removes_trailing_answered_line(self) -> None:
        assert strip_meta_artifacts('Reply.\nanswered = true') == 'Reply.'

    def test_removes_trailing_category_line(self) -> None:
        assert strip_meta_artifacts('Reply.\ncategory: skills') == 'Reply.'

    def test_keeps_a_clean_reply_untouched(self) -> None:
        assert strip_meta_artifacts('Just an answer.') == 'Just an answer.'

    def test_empty_string_stays_empty(self) -> None:
        assert strip_meta_artifacts('') == ''


# --- EVENT CONSTRUCTORS ---
class TestEventConstructors:

    def test_token_event_carries_the_content(self) -> None:
        assert token_event('hi') == {'type': 'token', 'content': 'hi'}

    def test_stream_end_event_has_no_payload(self) -> None:
        assert stream_end_event() == {'type': 'stream_end'}

    def test_ready_event_carries_the_session(self) -> None:
        assert ready_event('s-1') == {'type': 'ready', 'sessionId': 's-1'}

    def test_error_event_carries_code_and_message(self) -> None:
        event = error_event('timeout', 'too slow')
        assert event == {
            'type': 'error', 'error_code': 'timeout', 'message': 'too slow'
        }

    def test_done_event_without_exchange_id_omits_the_key(self) -> None:
        # a cache hit creates no exchange, so the client gets no id to rate
        assert 'exchangeId' not in done_event(True, 'skills')

    def test_done_event_with_exchange_id_includes_it(self) -> None:
        assert done_event(True, 'skills', 'ex-1')['exchangeId'] == 'ex-1'


class TestFormatSse:

    def test_wraps_the_event_in_an_sse_frame(self) -> None:
        assert format_sse({'type': 'stream_end'}) == (
            'data: {"type": "stream_end"}\n\n'
        )

    def test_payload_is_valid_json(self) -> None:
        frame = format_sse(token_event('oi'))
        assert json.loads(frame.removeprefix('data: ')) == {
            'type': 'token', 'content': 'oi'
        }

    def test_non_ascii_survives_the_round_trip(self) -> None:
        frame = format_sse(token_event('ação 😄'))
        assert json.loads(frame.removeprefix('data: '))['content'] == 'ação 😄'


# --- ERROR CLASSIFICATION ---
class TestClassifyStreamError:

    @pytest.mark.parametrize(
        ('error', 'code'),
        [
            (TimeoutError(), 'timeout'),
            (VectorStoreUnavailableError(), 'unavailable'),
            (RuntimeError('unmapped'), 'unknown'),
        ],
    )
    def test_maps_the_error_to_its_code(
        self, error: Exception, code: str
    ) -> None:
        assert classify_stream_error(error)[0] == code

    @pytest.mark.parametrize(
        ('cls', 'status', 'code'),
        [
            (openai.RateLimitError, 429, 'rate_limit'),
            (openai.AuthenticationError, 401, 'auth'),
        ],
    )
    def test_maps_provider_errors_by_type(
        self, cls: type, status: int, code: str
    ) -> None:
        error = _openai_error(cls, status)
        assert classify_stream_error(error)[0] == code

    def test_the_specific_type_wins_over_its_base(self) -> None:
        # RateLimitError is an APIError; the table is ordered so the narrower
        # entry matches first
        error = _openai_error(openai.RateLimitError, 429)
        assert classify_stream_error(error)[0] != 'unavailable'

    def test_the_message_never_leaks_internals(self) -> None:
        _, message = classify_stream_error(RuntimeError('db password is 123'))
        assert '123' not in message
