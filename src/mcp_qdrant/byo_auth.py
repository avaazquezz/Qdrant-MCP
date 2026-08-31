"""Per-request Qdrant target resolution for the public "bring your own
Qdrant" instance.

Reuses the `Authorization` and `x-api-key` headers for a different purpose
than their name suggests: verified hands-on against a real Claude.ai
account that a custom connector's "Request headers" UI only accepts
pre-approved header names without Anthropic's manual approval — a
made-up name like `X-Qdrant-Url` is rejected outright. `Authorization`
carries the caller's own Qdrant URL (sent verbatim, no forced `Bearer`
prefix), `x-api-key` optionally carries their Qdrant API key.
"""

from __future__ import annotations

from typing import Protocol

from qdrant_client import AsyncQdrantClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from mcp_qdrant.byo_qdrant import current_qdrant_client
from mcp_qdrant.ssrf_guard import PrivateHostError, assert_public_qdrant_url


class _ClientCache(Protocol):
    async def get_or_create(self, url: str, api_key: str | None) -> AsyncQdrantClient: ...


class BYOQdrantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, cache: _ClientCache) -> None:
        super().__init__(app)
        self._cache = cache

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url = request.headers.get("authorization")
        if not url:
            return JSONResponse(
                {
                    "error": "Missing required 'Authorization' header: set it to your "
                    "own Qdrant URL, e.g. https://xyz.cloud.qdrant.io:6333. "
                    "Optionally set 'x-api-key' to your Qdrant API key."
                },
                status_code=400,
            )
        try:
            await assert_public_qdrant_url(url)
        except PrivateHostError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

        client = await self._cache.get_or_create(url, request.headers.get("x-api-key") or None)
        token = current_qdrant_client.set(client)
        try:
            return await call_next(request)
        finally:
            current_qdrant_client.reset(token)
