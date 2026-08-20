"""
Unit tests for POST /chatbot/response/stream (SSE contract).
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from src.schemas.outputparser import ResponseOutputParser
from src.services.chatbot import cache
from src.services.chatbot.events import error_event
from src.services.chatbot.events import stream_end_event
from src.services.chatbot.events import token_event
from tests.unit.conftest import FakeRedis
from tests.unit.conftest import chat_payload
from typing import Any
from uuid import UUID

import json
import pytest


# --- HELPERS ---
def parse_sse(body: str) -> list[dict]:
    """Parses an SSE body into the list of event dicts."""
    events = []
    for frame in body.split('\n\n'):
        if frame.startswith('data: '):
            events.append(json.loads(frame[len('data: ') :]))
    return events


def seed_cache(fake_redis: FakeRedis, query: str, response: str) -> None:
    """Stores a cached response exactly like the cache service does."""
    fake_redis.data[cache._cache_key(query)] = json.dumps(
        {
            'response': response,
            'answered': True,
            'category': 'skills',
        }
    )


# --- CACHE-HIT PATH ---
def test_stream_cache_hit_contract(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_cache(fake_redis, 'Voce conhece Python?', 'Sim! Uso <b>Python</b>.')

    scheduled = []

    async def fake_schedule_memory_update(*args: object) -> None:
        scheduled.append(args)

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.schedule_memory_update',
        fake_schedule_memory_update,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')

    events = parse_sse(response.text)
    types = [e['type'] for e in events]

    # ready first, tokens, stream_end, then the terminal done
    assert types[0] == 'ready'
    assert events[0]['sessionId'] == 'test-session-123'
    assert types[-2] == 'stream_end'
    assert types[-1] == 'done'
    assert all(t == 'token' for t in types[1:-2])

    # tokens carry the response sanitized exactly ONCE (< becomes &lt;)
    streamed = ''.join(e['content'] for e in events if e['type'] == 'token')
    assert streamed == 'Sim! Uso &lt;b&gt;Python&lt;/b&gt;.'

    # a cache hit is a real exchange and is recorded like any other, so it
    # carries an exchangeId the visitor can send feedback about
    UUID(events[-1]['exchangeId'])

    # memory continuity preserved with the ORIGINAL (unsanitized) text
    assert scheduled == [
        ('test-session-123', 'Voce conhece Python?', 'Sim! Uso <b>Python</b>.')
    ]


# --- LIVE PATH ---
def test_stream_live_path_contract(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_prepare(state: dict) -> dict:
        return state

    async def fake_stream_answer(state: dict):
        yield token_event('Ola')
        yield token_event(' mundo')
        yield stream_end_event()
        state['response'] = ResponseOutputParser(
            response='Ola mundo', answered=True, category='general'
        )

    persisted: dict[str, Any] = {}

    async def fake_schedule_persistence(**kwargs: object) -> None:
        persisted.update(kwargs)

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.prepare_state', fake_prepare
    )
    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.stream_answer',
        fake_stream_answer,
    )
    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.schedule_persistence',
        fake_schedule_persistence,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    events = parse_sse(response.text)
    types = [e['type'] for e in events]

    assert types == ['ready', 'token', 'token', 'stream_end', 'done']

    done = events[-1]
    assert done['answered'] is True
    assert done['category'] == 'general'
    # live answers create an exchange: id present and a valid UUID
    UUID(done['exchangeId'])

    # persistence enqueued once the stream completed
    assert persisted['session_id'] == 'test-session-123'
    assert persisted['response_state']['response'].response == 'Ola mundo'


def test_stream_headers_disable_buffering(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_prepare(state: dict) -> dict:
        return state

    async def fake_stream_answer(state: dict):
        yield stream_end_event()
        state['response'] = ResponseOutputParser(
            response='x', answered=True, category='general'
        )

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.prepare_state', fake_prepare
    )
    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.stream_answer',
        fake_stream_answer,
    )

    async def fake_schedule_persistence(**kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.schedule_persistence',
        fake_schedule_persistence,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    assert response.headers['cache-control'] == 'no-cache'
    assert response.headers['x-accel-buffering'] == 'no'


# --- ERROR MID-STREAM ---
def test_stream_error_emits_error_and_skips_done_and_persistence(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_prepare(state: dict) -> dict:
        return state

    async def fake_stream_answer(state: dict):
        yield token_event('parcial')
        yield error_event('timeout', 'The response took too long.')
        # errored: state['response'] intentionally NOT set

    persisted = []

    async def fake_schedule_persistence(**kwargs: object) -> None:
        persisted.append(kwargs)

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.prepare_state', fake_prepare
    )
    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.stream_answer',
        fake_stream_answer,
    )
    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.schedule_persistence',
        fake_schedule_persistence,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    events = parse_sse(response.text)
    types = [e['type'] for e in events]

    assert 'error' in types
    # a broken stream must never emit a done event nor persist/cache
    assert 'done' not in types
    assert persisted == []

    error = next(e for e in events if e['type'] == 'error')
    assert error['error_code'] == 'timeout'


# --- ERRORS BEFORE THE STREAM STARTS ---
def test_pre_stream_failure_returns_http_error_not_sse(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # message resolution (e.g. audio transcription) happens BEFORE the
    # streamingResponse: its failure must surface as a normal HTTP error.
    from src.errors.transcription_error import TranscriptionError

    async def failing_resolve(payload: object) -> str:
        raise TranscriptionError()

    monkeypatch.setattr(
        'src.services.chatbot.pipeline.resolve_message',
        failing_resolve,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert response.json()['error'] == 'transcription_error'


# --- UNEXPECTED EXCEPTION MID-STREAM ---
def test_unexpected_exception_mid_stream_yields_error_frame(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exploding_prepare(state: dict) -> dict:
        raise RuntimeError('boom interno')

    monkeypatch.setattr(
        'src.services.chatbot.respond_stream.prepare_state',
        exploding_prepare,
    )

    response = client.post(
        '/api/chatbot/response/stream',
        json=chat_payload(),
        headers=auth_headers,
    )
    # the stream already started (200): the error arrives as an SSE frame
    assert response.status_code == 200
    events = parse_sse(response.text)
    error = next(e for e in events if e['type'] == 'error')
    assert error['error_code'] == 'unknown'
    # internal details must never leak to the client
    assert 'boom interno' not in response.text
