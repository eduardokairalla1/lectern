"""
Unit tests for API key authentication on protected endpoints.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from tests.unit.conftest import chat_payload

import pytest


PROTECTED_ENDPOINTS = [
    '/api/chatbot/response',
    '/api/chatbot/response/stream',
    '/api/chatbot/feedback/exchange/4b1e6b8a-3f2c-4a5d-9e8f-1a2b3c4d5e6f',
    '/api/chatbot/feedback/session/test-session-123',
]


# --- TESTS ---
@pytest.mark.parametrize('endpoint', PROTECTED_ENDPOINTS)
def test_wrong_api_key_returns_401(
    client: TestClient, endpoint: str
) -> None:
    response = client.post(
        endpoint,
        json=chat_payload(),
        headers={'x-api-key': 'wrong-key-000000000000000000000000'},
    )
    assert response.status_code == 401
    assert response.json()['error'] == 'unauthorized_error'


@pytest.mark.parametrize('endpoint', PROTECTED_ENDPOINTS)
def test_missing_api_key_returns_401(
    client: TestClient, endpoint: str
) -> None:
    # missing credentials are an auth failure (401), not a schema error:
    # the response must not hint that the header exists or how it is named.
    response = client.post(endpoint, json=chat_payload())
    assert response.status_code == 401
    assert response.json()['error'] == 'unauthorized_error'


def test_empty_api_key_returns_401(client: TestClient) -> None:
    response = client.post(
        '/api/chatbot/response',
        json=chat_payload(),
        headers={'x-api-key': ''},
    )
    assert response.status_code == 401


def test_correct_api_key_reaches_the_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_respond(
        payload: object, request_ip: object, user_agent: object
    ) -> dict:
        return {'response': 'ok', 'exchangeId': 'abc'}

    monkeypatch.setattr('src.routers.chatbot.respond', fake_respond)

    response = client.post(
        '/api/chatbot/response', json=chat_payload(), headers=auth_headers
    )
    assert response.status_code == 200


def test_unauthorized_body_does_not_leak_details(
    client: TestClient,
) -> None:
    body = client.post('/api/chatbot/response', json=chat_payload()).json()
    # only the stable slug and the generic message, no internals
    assert set(body.keys()) == {'error', 'message'}
