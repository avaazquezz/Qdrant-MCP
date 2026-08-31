"""Unit tests for SharedSecretMiddleware: no real Qdrant, no real network —
drives a minimal Starlette app through httpx's in-process ASGI transport.
"""

from __future__ import annotations

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mcp_qdrant.http_auth import SharedSecretMiddleware


def _build_app(secret: str) -> Starlette:
    async def ok(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/mcp", ok)])
    app.add_middleware(SharedSecretMiddleware, secret=secret)
    return app


async def _client(app: Starlette) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_missing_authorization_header_returns_401() -> None:
    async with await _client(_build_app("s3cr3t")) as client:
        response = await client.get("/mcp")
    assert response.status_code == 401


async def test_wrong_secret_returns_401() -> None:
    async with await _client(_build_app("s3cr3t")) as client:
        response = await client.get("/mcp", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


async def test_correct_secret_passes_through() -> None:
    async with await _client(_build_app("s3cr3t")) as client:
        response = await client.get("/mcp", headers={"Authorization": "Bearer s3cr3t"})
    assert response.status_code == 200
    assert response.text == "ok"
