"""
Unit tests for the scoped CORS middleware and /whoami.
"""

# --- IMPORTS ---
from fastapi.testclient import TestClient
from src.middleware.cors import ScopedCORSMiddleware


PROD_ORIGIN = 'https://configured-origin.example'
ACAO = 'access-control-allow-origin'


# --- WHOAMI ---
def test_whoami_returns_public_profile(client: TestClient) -> None:
    response = client.get('/api/whoami')
    assert response.status_code == 200
    body = response.json()
    assert body['name']
    assert isinstance(body['name'], str)


def test_whoami_requires_no_api_key(client: TestClient) -> None:
    assert client.get('/api/whoami').status_code == 200


def test_whoami_is_open_to_any_origin(client: TestClient) -> None:
    response = client.get(
        '/api/whoami', headers={'Origin': 'https://qualquer-site.com'}
    )
    assert response.headers[ACAO] == '*'


# --- SCOPED CORS: integration ---
def test_allowed_origin_is_echoed_with_vary(client: TestClient) -> None:
    # the app is built from config.CORS_ORIGINS, which no longer names any
    # particular domain, so the check goes through the middleware directly
    allowed = _middleware()._allow_origin_for('/api/system/health', PROD_ORIGIN)
    assert allowed == PROD_ORIGIN

    response = client.get('/api/system/health',
                          headers={'Origin': 'http://localhost:3000'})
    assert response.headers[ACAO] == 'http://localhost:3000'
    assert 'Origin' in response.headers.get('vary', '')


def test_localhost_any_port_is_allowed(client: TestClient) -> None:
    for origin in ['http://localhost:3000', 'http://localhost:61234']:
        response = client.get('/api/system/health', headers={'Origin': origin})
        assert response.headers[ACAO] == origin


def test_unknown_origin_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get(
        '/api/system/health', headers={'Origin': 'https://evil.com'}
    )
    assert ACAO not in response.headers


def test_localhost_lookalike_domain_is_rejected(client: TestClient) -> None:
    response = client.get(
        '/api/system/health',
        headers={'Origin': 'http://localhost.evil.com:3000'},
    )
    assert ACAO not in response.headers


def test_preflight_is_answered_directly(client: TestClient) -> None:
    response = client.options(
        '/api/chatbot/response',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'POST',
        },
    )
    assert response.status_code == 204
    assert response.headers[ACAO] == 'http://localhost:5173'
    assert 'POST' in response.headers['access-control-allow-methods']
    # the custom auth header must be preflight-allowed
    allowed = response.headers['access-control-allow-headers'].lower()
    assert 'x-api-key' in allowed


def test_preflight_from_unknown_origin_has_no_acao(
    client: TestClient,
) -> None:
    response = client.options(
        '/api/chatbot/response',
        headers={
            'Origin': 'https://evil.com',
            'Access-Control-Request-Method': 'POST',
        },
    )
    assert response.status_code == 204
    assert ACAO not in response.headers


# --- SCOPED CORS: unit (_allow_origin_for) ---
def _middleware() -> ScopedCORSMiddleware:
    return ScopedCORSMiddleware(
        app=None,  # type: ignore[arg-type]
        allowed_origins=['http://localhost:*', PROD_ORIGIN],
    )


def test_allow_origin_public_path_is_wildcard() -> None:
    origin = _middleware()._allow_origin_for('/api/whoami', 'https://x.com')
    assert origin == '*'


def test_allow_origin_no_origin_header() -> None:
    assert _middleware()._allow_origin_for('/api/system/health', None) is None


def test_allow_origin_wildcard_requires_port_separator() -> None:
    middleware = _middleware()
    # 'http://localhost' without an explicit port does not match ':*'
    assert (
        middleware._allow_origin_for('/x', 'http://localhost') is None
    )
    assert (
        middleware._allow_origin_for('/x', 'http://localhost:80')
        == 'http://localhost:80'
    )
