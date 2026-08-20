"""
Unit tests for system endpoints.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from src.app import app
from src.resources import set_resources
from tests.unit.conftest import make_fake_resources

import pytest


# --- TESTS ---
def test_health_returns_200(client: TestClient) -> None:
    response = client.get('/api/system/health')
    assert response.status_code == 200


def test_health_status_is_ok_after_startup(client: TestClient) -> None:
    assert client.get('/api/system/health').json()['status'] == 'OK'


def test_info_returns_200(client: TestClient) -> None:
    response = client.get('/api/system/info')
    assert response.status_code == 200


def test_info_body_has_required_fields(client: TestClient) -> None:
    data = client.get('/api/system/info').json()
    assert 'name' in data
    assert 'description' in data
    assert 'version' in data
    assert 'extra' in data


def test_info_matches_app_metadata(client: TestClient) -> None:
    data = client.get('/api/system/info').json()
    assert data['name'] == app.title
    assert data['version'] == app.version


def test_system_endpoints_do_not_require_api_key(client: TestClient) -> None:
    # health/info are infra probes: they must work without credentials
    assert client.get('/api/system/health').status_code == 200
    assert client.get('/api/system/info').status_code == 200


def test_repeated_startups_do_not_duplicate_routes() -> None:
    # route mounting must be idempotent across lifespan restarts (each
    # TestClient run triggers a full startup/shutdown cycle). Shutdown
    # clears the resources container, so fakes are reinstalled per run.
    route_count = len(app.routes)
    try:
        for _ in range(2):
            set_resources(make_fake_resources())
            with TestClient(app):
                pass
    finally:
        set_resources(None)
    assert len(app.routes) == route_count


# --- ERROR CONTRACT ---
@pytest.mark.parametrize(
    ('method', 'path', 'status'),
    [
        ('get', '/rota-inexistente', 404),
        ('post', '/api/system/health', 405),
    ],
)
def test_framework_errors_use_the_json_error_envelope(
    client: TestClient, method: str, path: str, status: int
) -> None:
    """404/405 come from Starlette's router, not from our code, and must
    still answer with {'error', 'message'} like every other failure."""
    response = getattr(client, method)(path)

    assert response.status_code == status
    body = response.json()
    assert body['error'] == 'http_error'
    assert isinstance(body['message'], str)
