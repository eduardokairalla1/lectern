"""
Path-scoped CORS middleware.

We need two different CORS policies on the same app:
- /whoami is a public, read-only endpoint → any origin may read it (`*`).
- everything else (the chatbot API) → only the configured origins (and localhost
  in dev), taken from config.CORS_ORIGINS.

Starlette's built-in CORSMiddleware applies a single origin policy to the whole
app, so it can't express this. This is a small pure-ASGI middleware (it only
injects response headers and answers preflight): it does NOT buffer the
response, so it is safe in front of the SSE streaming endpoint.

Note: CORS is a browser-only guardrail (it stops other sites' JavaScript from
READING the response). It is NOT access control: non-browser clients ignore it.
"""

# --- IMPORTS ---
from collections.abc import Iterable
from src.config import config
from starlette.datastructures import Headers
from starlette.datastructures import MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send


# --- CONFIG ---
PUBLIC_PATHS = frozenset({f'{config.API_PREFIX}/whoami'})
ALLOWED_METHODS = 'GET, POST, OPTIONS'
ALLOWED_HEADERS = 'Content-Type, x-api-key'
PREFLIGHT_MAX_AGE = '600'


# --- MIDDLEWARE ---
class ScopedCORSMiddleware:
    """
    Applies open CORS to PUBLIC_PATHS and a restricted policy elsewhere.
    """

    def __init__(self, app: ASGIApp, allowed_origins: Iterable[str]) -> None:
        """
        Initializes the middleware.

        :param app: The ASGI application to wrap.
        :param allowed_origins: Origins allowed outside PUBLIC_PATHS. An
            entry ending in ':*' matches any port on that host.

        :return: None.
        """
        # get the app and allowed origins
        self.app = app
        origins = frozenset(allowed_origins)

        # split the allowed origins
        self.wildcard_port_prefixes = tuple(
            o[:-1] for o in origins if o.endswith(':*')
        )
        self.allowed_origins = frozenset(
            o for o in origins if not o.endswith(':*')
        )

    def _allow_origin_for(self, path: str, origin: str | None) -> str | None:
        """
        Resolves the Access-Control-Allow-Origin value for a request.

        :param path: The requested path.
        :param origin: The request's Origin header, if it carries one.

        :return: The header value, or None when the origin is not allowed.
        """
        # public path: same answer for everyone
        if path in PUBLIC_PATHS:
            return '*'

        # origin is allowed: return it
        if origin and (origin in self.allowed_origins or
                       origin.startswith(self.wildcard_port_prefixes)):
            return origin

        # origin is not allowed: return None
        return None


    @staticmethod
    def _apply_cors(headers: MutableHeaders, allow_origin: str | None) -> None:
        """
        Writes the CORS headers for a resolved origin.

        :param headers: Response headers to write into.
        :param allow_origin: Resolved origin, or None to write nothing.

        :return: None.
        """
        # origin not allowed: leave the response untouched
        if not allow_origin:
            return

        # write the CORS headers
        headers['Access-Control-Allow-Origin'] = allow_origin

        # origin is not '*': add Vary
        if allow_origin != '*':
            headers.add_vary_header('Origin')


    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:
        """
        Answers preflight requests and adds CORS headers to responses.

        :param scope: The ASGI connection scope.
        :param receive: The ASGI receive callable.
        :param send: The ASGI send callable.

        :return: None.
        """
        # not HTTP (websocket, lifespan): nothing to do
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # resolve the allowed origin for this request
        headers = Headers(scope=scope)
        allow_origin = self._allow_origin_for(
            scope['path'], headers.get('origin')
        )

        # this is a preflight request: answer it and return
        if (scope['method'] == 'OPTIONS' and
           'access-control-request-method' in headers):
            response = Response(
                status_code=204,
                headers={
                    'Access-Control-Allow-Methods': ALLOWED_METHODS,
                    'Access-Control-Allow-Headers': ALLOWED_HEADERS,
                    'Access-Control-Max-Age': PREFLIGHT_MAX_AGE,
                },
            )
            self._apply_cors(response.headers, allow_origin)
            await response(scope, receive, send)
            return

        # real request: inject the headers into the response start message
        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                self._apply_cors(MutableHeaders(scope=message), allow_origin)
            await send(message)

        # forward the request to the app
        await self.app(scope, receive, send_wrapper)
