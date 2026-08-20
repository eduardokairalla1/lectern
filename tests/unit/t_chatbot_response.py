"""
Unit tests for POST /chatbot/response and the respond orchestrator.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from src.app import app
from src.errors.processing_error import ProcessingError
from src.errors.vector_store_unavailable_error import (
    VectorStoreUnavailableError,
)
from src.resources import Resources
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.schemas.outputparser import ResponseOutputParser
from src.services.chatbot import cache
from src.services.chatbot.respond import respond
from src.services.chatbot.types import ChatMessage
from tests.unit.conftest import chat_payload
from typing import Any
from uuid import UUID

import pytest


# --- ENDPOINT: happy path ---
def test_response_returns_service_result(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    async def fake_respond(
        chat_message: ChatMessage, request_ip: object, user_agent: object
    ) -> dict:
        captured['session'] = chat_message.session_id
        return {'response': 'Sim, conheco Python!', 'exchangeId': 'c-1'}

    monkeypatch.setattr('src.routers.chatbot.respond', fake_respond)

    response = client.post(
        '/api/chatbot/response', json=chat_payload(), headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body['response'] == 'Sim, conheco Python!'
    assert body['exchangeId'] == 'c-1'
    assert captured['session'] == 'test-session-123'


# --- ENDPOINT: service errors map to the declared status codes ---
@pytest.mark.parametrize(
    ('error', 'status', 'slug'),
    [
        (ProcessingError, 500, 'processing_error'),
        (VectorStoreUnavailableError, 502, 'vector_store_unavailable_error'),
    ],
)
def test_response_service_error_maps_to_status(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    error: type,
    status: int,
    slug: str,
) -> None:
    async def failing_respond(
        payload: object, request_ip: object, user_agent: object
    ) -> dict:
        raise error({'detail': 'internal-only'})

    monkeypatch.setattr('src.routers.chatbot.respond', failing_respond)

    response = client.post(
        '/api/chatbot/response', json=chat_payload(), headers=auth_headers
    )
    assert response.status_code == status
    body = response.json()
    assert body['error'] == slug
    # internal details are logged, never returned
    assert 'internal-only' not in response.text


def test_response_unexpected_error_still_returns_json(
    resources: Resources,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error that is not a BackendError must keep the JSON contract."""

    async def failing_respond(
        payload: object, request_ip: object, user_agent: object
    ) -> dict:
        raise RuntimeError('internal-only')

    monkeypatch.setattr('src.routers.chatbot.respond', failing_respond)

    # the server re-raises after responding, so the response has to be read
    # with re-raising turned off
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            '/api/chatbot/response', json=chat_payload(), headers=auth_headers
        )

    assert response.status_code == 500
    assert response.headers['content-type'].startswith('application/json')
    assert response.json()['error'] == 'processing_error'
    # internal details are logged, never returned
    assert 'internal-only' not in response.text


# --- ENDPOINT: request validation ---
def test_response_invalid_session_id_returns_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        '/api/chatbot/response',
        json=chat_payload(session_id='bad'),
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_request_error'


def test_response_content_too_long_returns_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        '/api/chatbot/response',
        json=chat_payload(message='a' * 301),
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_response_missing_message_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        '/api/chatbot/response',
        json={'sessionId': 'test-session-123'},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()['error'] == 'request_validation_error'


def test_response_malformed_json_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        '/api/chatbot/response',
        content=b'{not json',
        headers={**auth_headers, 'Content-Type': 'application/json'},
    )
    assert response.status_code == 422


# --- SERVICE: respond orchestration ---
def _chat_message() -> ChatMessage:
    return ChatMessage.from_payload(ChatbotPayload(**chat_payload()))


@pytest.mark.anyio
async def test_respond_cache_hit_returns_cached_and_updates_memory(
    resources: Resources, monkeypatch: pytest.MonkeyPatch
) -> None:
    # seed the cache through the real cache service (same key derivation)
    await cache.set_cached_response(
        query='Voce conhece Python?',
        response='Resposta cacheada',
        answered=True,
        category='skills',
    )

    scheduled = []

    async def fake_schedule_memory_update(*args: object) -> None:
        scheduled.append(args)

    monkeypatch.setattr(
        'src.services.chatbot.respond.schedule_memory_update',
        fake_schedule_memory_update,
    )
    # the cache path now persists an exchange: keep the real broker out of it
    monkeypatch.setattr(
        'src.services.chatbot.persistence.dispatch_task',
        lambda task, **kwargs: None,
    )

    result = await respond(_chat_message(), request_ip=None, user_agent=None)

    assert result['response'] == 'Resposta cacheada'
    UUID(result['exchangeId'])
    # memory continuity must be preserved even on cache hits
    assert scheduled == [
        ('test-session-123', 'Voce conhece Python?', 'Resposta cacheada')
    ]


@pytest.mark.anyio
async def test_respond_cache_is_skipped_when_session_has_history(
    resources: Resources, monkeypatch: pytest.MonkeyPatch
) -> None:
    # a cached answer exists, but the session already has context: using the
    # cache would break conversation continuity.
    await cache.set_cached_response(
        query='Voce conhece Python?',
        response='Resposta cacheada',
        answered=True,
        category='skills',
    )

    async def fake_recent(session_id: str) -> list:
        return [('pergunta anterior', 'resposta anterior')]

    monkeypatch.setattr(
        'src.services.chatbot.pipeline.memory.get_recent_interactions',
        fake_recent,
    )

    async def fake_prepare(state: dict) -> dict:
        return state

    async def fake_answer(state: dict) -> dict:
        state['response'] = ResponseOutputParser(
            response='Resposta nova', answered=True, category='skills'
        )
        return state

    monkeypatch.setattr(
        'src.services.chatbot.respond.prepare_state', fake_prepare
    )
    monkeypatch.setattr('src.services.chatbot.respond.answer', fake_answer)

    async def fake_schedule_persistence(**kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        'src.services.chatbot.respond.schedule_persistence',
        fake_schedule_persistence,
    )

    result = await respond(_chat_message(), request_ip=None, user_agent=None)
    assert result['response'] == 'Resposta nova'


@pytest.mark.anyio
async def test_respond_fresh_path_returns_exchange_id_and_persists(
    resources: Resources, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_prepare(state: dict) -> dict:
        return state

    async def fake_answer(state: dict) -> dict:
        state['response'] = ResponseOutputParser(
            response='Resposta gerada', answered=True, category='projects'
        )
        return state

    persisted: dict[str, Any] = {}

    async def fake_persistence(**kwargs: object) -> None:
        persisted.update(kwargs)

    monkeypatch.setattr(
        'src.services.chatbot.respond.prepare_state', fake_prepare
    )
    monkeypatch.setattr('src.services.chatbot.respond.answer', fake_answer)
    monkeypatch.setattr(
        'src.services.chatbot.respond.schedule_persistence', fake_persistence
    )

    result = await respond(_chat_message(), request_ip=None, user_agent=None)

    assert result['response'] == 'Resposta gerada'
    # the exchange id must be a valid UUID the client can use for feedback
    UUID(result['exchangeId'])
    # stats/cache/memory persistence enqueued with the final state
    assert persisted['session_id'] == 'test-session-123'
    assert persisted['user_message'] == 'Voce conhece Python?'
    assert persisted['response_state']['response'].response == (
        'Resposta gerada'
    )
    assert persisted['total_duration_ms'] >= 0


@pytest.mark.anyio
async def test_cache_hit_is_recorded_as_an_exchange(
    resources: Resources, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cache hit is a real question from a real visitor. Recording it is
    what keeps the most popular questions from disappearing from the
    analytics, and served_from_cache is what stops those zero-token rows
    from reading as free generations."""
    await cache.set_cached_response(
        query='Voce conhece Python?',
        response='Resposta cacheada',
        answered=True,
        category='skills',
    )

    dispatched: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        'src.services.chatbot.persistence.dispatch_task',
        lambda task, **kwargs: dispatched.append((task.name, kwargs)),
    )

    await respond(
        _chat_message(), request_ip='203.0.113.7', user_agent='pytest'
    )

    saved = [kwargs for name, kwargs in dispatched
             if name == 'chatbot.save_exchange_stats']
    assert len(saved) == 1
    assert saved[0]['session_data'] == {
        'id': 'test-session-123',
        'request_ip': '203.0.113.7',
        'user_agent': 'pytest',
    }
    exchange = saved[0]['exchange_data']
    assert exchange['served_from_cache'] is True
    assert exchange['assistant_response'] == 'Resposta cacheada'
    assert exchange['topic_category'] == 'skills'
    # no model was called, so there is nothing to bill to this exchange
    assert saved[0]['executions'] == []
    # retrieval and rewrite never ran: absent says that, [] would not
    assert 'retrieved_documents' not in exchange
    assert 'rewritten_query' not in exchange
