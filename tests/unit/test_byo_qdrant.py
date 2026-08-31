"""Unit tests for BYOQdrantClientProxy: no real Qdrant needed."""

from __future__ import annotations

import pytest

from mcp_qdrant.byo_qdrant import BYOQdrantClientProxy, current_qdrant_client
from mcp_qdrant.qdrant_client_cache import QdrantClientCache
from mcp_qdrant.tools.errors import NoQdrantClientError


class _StubClient:
    async def get_collections(self) -> str:
        return "stub-result"


def test_attribute_access_without_bound_client_raises() -> None:
    proxy = BYOQdrantClientProxy(QdrantClientCache())
    with pytest.raises(NoQdrantClientError):
        getattr(proxy, "get_collections")  # noqa: B009


def test_attribute_access_delegates_to_bound_client() -> None:
    proxy = BYOQdrantClientProxy(QdrantClientCache())
    token = current_qdrant_client.set(_StubClient())  # type: ignore[arg-type]
    try:
        assert proxy.get_collections is not None
    finally:
        current_qdrant_client.reset(token)
