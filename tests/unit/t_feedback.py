"""
Unit tests for POST /chatbot/feedback/exchange/{exchangeId}.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from types import SimpleNamespace

import pytest


VALID_UUID = '4b1e6b8a-3f2c-4a5d-9e8f-1a2b3c4d5e6f'


# --- HELPERS ---
@pytest.fixture
def captured_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Replaces the Celery task with a recorder (exercises _dispatch)."""
    calls: list[dict] = []
    fake_task = SimpleNamespace(
        delay=lambda **kwargs: calls.append(kwargs),
        name='chatbot.save_feedback',
    )
    monkeypatch.setattr(
        'src.services.chatbot.persistence.save_feedback', fake_task
    )
    return calls


# --- TESTS ---
def test_feedback_is_accepted_and_enqueued(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    response = client.post(
        f'/api/chatbot/feedback/exchange/{VALID_UUID}',
        json={
            'rating': 'up',
            'comment': 'muito bom!',
        },
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert response.json() == {'status': 'accepted'}
    assert captured_dispatch == [
        {
            'exchange_id': VALID_UUID,
            'rating': 'up',
            'comment': 'muito bom!',
        }
    ]


def test_feedback_comment_is_optional(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    response = client.post(
        f'/api/chatbot/feedback/exchange/{VALID_UUID}',
        json={'exchangeId': VALID_UUID, 'rating': 'down'},
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert captured_dispatch[0]['rating'] == 'down'
    assert captured_dispatch[0]['comment'] is None


def test_feedback_broker_outage_still_returns_202(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # dispatch is best-effort: a broker outage must never fail the request
    def broken_delay(**kwargs: object) -> None:
        raise ConnectionError('broker is down')

    fake_task = SimpleNamespace(
        delay=broken_delay, name='chatbot.save_feedback'
    )
    monkeypatch.setattr(
        'src.services.chatbot.persistence.save_feedback', fake_task
    )

    response = client.post(
        f'/api/chatbot/feedback/exchange/{VALID_UUID}',
        json={'exchangeId': VALID_UUID, 'rating': 'up'},
        headers=auth_headers,
    )
    assert response.status_code == 202


@pytest.mark.parametrize(
    'payload',
    [
        {'rating': 'excellent'},
        {'rating': 'up', 'comment': 'a' * 501},
    ],
)
def test_feedback_invalid_payload_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
    payload: dict,
) -> None:
    response = client.post(
        f'/api/chatbot/feedback/exchange/{VALID_UUID}',
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_request_error'
    # nothing may be enqueued for a rejected payload
    assert captured_dispatch == []


def test_feedback_missing_fields_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f'/api/chatbot/feedback/exchange/{VALID_UUID}',
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_feedback_invalid_exchange_id_in_path_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    """The identifier moved to the path, so a malformed one is rejected by
    the path dependency and must still answer 400, not FastAPI's 422."""
    response = client.post(
        '/api/chatbot/feedback/exchange/not-a-uuid',
        json={'rating': 'up'},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_request_error'
    assert captured_dispatch == []
