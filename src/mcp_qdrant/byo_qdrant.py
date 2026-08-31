"""Per-request Qdrant client resolution for BYO ("bring your own") mode.

Every tool module closes over a single `client` object passed once at
server-build time, and only touches it via lazy attribute lookups inside
`call_qdrant(lambda: client.something(...))` — the lookup happens at call
time, not at registration time. That means a duck-typed proxy that resolves
`current_qdrant_client` per request stands in for the real
`AsyncQdrantClient` everywhere, with zero changes to any tool file.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from qdrant_client import AsyncQdrantClient

from mcp_qdrant.qdrant_client_cache import QdrantClientCache
from mcp_qdrant.tools.errors import NoQdrantClientError

current_qdrant_client: ContextVar[AsyncQdrantClient] = ContextVar("current_qdrant_client")


class BYOQdrantClientProxy:
    """Stands in for AsyncQdrantClient; every attribute access resolves the
    client bound to the current request by BYOQdrantMiddleware."""

    def __init__(self, cache: QdrantClientCache) -> None:
        self._cache = cache

    def __getattr__(self, name: str) -> Any:
        try:
            client = current_qdrant_client.get()
        except LookupError as exc:
            raise NoQdrantClientError(
                "No Qdrant client bound to this request. This should have been "
                "rejected by BYOQdrantMiddleware before reaching a tool."
            ) from exc
        return getattr(client, name)

    async def close(self) -> None:
        await self._cache.aclose_all()
