"""Shared-secret auth for the `streamable-http` transport.

`MCPServer.run(transport="streamable-http")` builds and serves its own
Starlette app internally with no hook for middleware, so `cli.py` builds the
app itself via `server.streamable_http_app(...)` and wraps it with
`SharedSecretMiddleware` before serving it. Chosen header/scheme
(`Authorization: Bearer <secret>`) matches one of the two header names
Claude.ai's remote-connector "Request headers" UI sends without needing
Anthropic's manual approval for a custom header name — verified hands-on
against a real Claude.ai account.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SharedSecretMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, secret: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {secret}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.headers.get("authorization") != self._expected:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)
