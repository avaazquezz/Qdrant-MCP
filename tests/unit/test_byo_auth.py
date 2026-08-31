"""Unit tests for BYOQdrantMiddleware: no real Qdrant, no real network —
drives a minimal Starlette app through httpx's in-process ASGI transport,
with a stub client cache so no real AsyncQdrantClient is ever constructed.
"""

from __future__ import annotations

import asyncio

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mcp_qdrant.byo_auth import BYOQdrantMiddleware
from mcp_qdrant.byo_qdrant import current_qdrant_client


class _StubCache:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def get_or_create(self, url: str, api_key: str | None) -> str:
        self.calls.append((url, api_key))
        return f"client-for-{url}"


def _build_app(cache: _StubCache) -> Starlette:
    async def echo_client(request: Request) -> PlainTextResponse:
        # The stub cache hands back a plain str, not a real AsyncQdrantClient —
        # fine at runtime (BYOQdrantMiddleware never inspects the client's
        # type), but it means this file intentionally violates the contextvar's
        # AsyncQdrantClient annotation.
        return PlainTextResponse(current_qdrant_client.get())

    app = Starlette(routes=[Route("/mcp", echo_client)])
    app.add_middleware(BYOQdrantMiddleware, cache=cache)  # type: ignore[arg-type]
    return app


async def _client(app: Starlette) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_missing_authorization_header_returns_400() -> None:
    async with await _client(_build_app(_StubCache())) as client:
        response = await client.get("/mcp")
    assert response.status_code == 400
    assert "Authorization" in response.json()["error"]


async def test_private_host_returns_400() -> None:
    async with await _client(_build_app(_StubCache())) as client:
        response = await client.get("/mcp", headers={"Authorization": "http://127.0.0.1:6333"})
    assert response.status_code == 400


async def test_valid_public_url_resolves_client_and_passes_through() -> None:
    cache = _StubCache()
    async with await _client(_build_app(cache)) as client:
        response = await client.get(
            "/mcp",
            headers={"Authorization": "http://8.8.8.8:6333", "x-api-key": "my-key"},
        )
    assert response.status_code == 200
    assert response.text == "client-for-http://8.8.8.8:6333"
    assert cache.calls == [("http://8.8.8.8:6333", "my-key")]


async def test_concurrent_requests_see_their_own_client() -> None:
    cache = _StubCache()
    async with await _client(_build_app(cache)) as client:
        responses = await asyncio.gather(
            client.get("/mcp", headers={"Authorization": "http://8.8.8.8:6333"}),
            client.get("/mcp", headers={"Authorization": "http://1.1.1.1:6333"}),
        )
    texts = {r.text for r in responses}
    assert texts == {"client-for-http://8.8.8.8:6333", "client-for-http://1.1.1.1:6333"}
