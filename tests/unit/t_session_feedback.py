"""
Unit tests for POST /chatbot/feedback/session/{sessionId}.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from httpx2 import Response
from types import SimpleNamespace

import pytest


VALID_SESSION = 'test-session-123'


# --- HELPERS ---
@pytest.fixture
def captured_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Replaces the Celery task with a recorder (exercises _dispatch)."""
    calls: list[dict] = []
    fake_task = SimpleNamespace(
        delay=lambda **kwargs: calls.append(kwargs),
        name='chatbot.save_session_feedback',
    )
    monkeypatch.setattr(
        'src.services.chatbot.persistence.save_session_feedback', fake_task
    )
    return calls


def post(
    client: TestClient,
    auth_headers: dict[str, str],
    **overrides: object,
) -> Response:
    """Posts a valid session rating, with fields overridden to break it."""
    session_id = overrides.pop('session_id', VALID_SESSION)
    payload: dict = {'score': 9}
    payload.update(overrides)
    return client.post(
        f'/api/chatbot/feedback/session/{session_id}',
        json=payload,
        headers=auth_headers,
    )


# --- TESTS ---
def test_session_feedback_is_accepted_and_enqueued(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    response = post(client, auth_headers, comment='achei o que precisava')

    assert response.status_code == 202
    assert response.json() == {'status': 'accepted'}
    assert captured_dispatch == [
        {
            'session_id': VALID_SESSION,
            'score': 9,
            'comment': 'achei o que precisava',
        }
    ]


def test_session_feedback_comment_is_optional(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    response = post(client, auth_headers)

    assert response.status_code == 202
    assert captured_dispatch[0]['comment'] is None


@pytest.mark.parametrize('score', [0, 10])
def test_session_feedback_score_boundaries_are_accepted(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
    score: int,
) -> None:
    assert post(client, auth_headers, score=score).status_code == 202


@pytest.mark.parametrize('score', [-1, 11])
def test_session_feedback_score_out_of_range_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
    score: int,
) -> None:
    assert post(client, auth_headers, score=score).status_code == 400
    assert captured_dispatch == []


def test_session_feedback_non_integer_score_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    """A fractional score is a schema violation, not a range one, so it is
    FastAPI's 422 rather than our 400."""
    assert post(client, auth_headers, score=8.5).status_code == 422


def test_session_feedback_invalid_session_id_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    assert post(client, auth_headers, session_id='short').status_code == 400
    assert captured_dispatch == []


def test_session_feedback_comment_over_limit_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    response = post(client, auth_headers, comment='a' * 1001)

    assert response.status_code == 400
    assert captured_dispatch == []


def test_session_feedback_requires_api_key(client: TestClient) -> None:
    response = client.post(
        f'/api/chatbot/feedback/session/{VALID_SESSION}',
        json={'score': 9},
    )
    assert response.status_code == 401


def test_session_feedback_broker_outage_still_returns_202(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dispatch_task swallows broker failures: the visitor already saw the
    conversation, so a dead broker must not turn their rating into a 500."""
    def explode(**kwargs: object) -> None:
        raise ConnectionError('broker is down')

    monkeypatch.setattr(
        'src.services.chatbot.persistence.save_session_feedback',
        SimpleNamespace(delay=explode, name='chatbot.save_session_feedback'),
    )

    assert post(client, auth_headers).status_code == 202


def test_session_may_be_rated_more_than_once(
    client: TestClient,
    auth_headers: dict[str, str],
    captured_dispatch: list[dict],
) -> None:
    """A conversation keeps growing, so a later rating judges a different
    amount of conversation: the endpoint must accept it rather than treat it
    as a duplicate."""
    assert post(client, auth_headers, score=9).status_code == 202
    assert post(client, auth_headers, score=3).status_code == 202

    assert [call['score'] for call in captured_dispatch] == [9, 3]
