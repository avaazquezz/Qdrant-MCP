"""Confirms the BYO proxy/cache chain really reaches a live Qdrant instance.

CI's only real Qdrant lives on loopback, which is exactly what
assert_public_qdrant_url exists to reject — this one test bypasses it (with
this comment as the reason) so it can drive a genuine AsyncQdrantClient
end-to-end. SSRF rejection itself is covered with zero mocking by
tests/unit/test_ssrf_guard.py.
"""

from __future__ import annotations

import os

import pytest

from mcp_qdrant.byo_qdrant import BYOQdrantClientProxy, current_qdrant_client
from mcp_qdrant.qdrant_client import ping
from mcp_qdrant.qdrant_client_cache import QdrantClientCache

pytestmark = pytest.mark.integration


async def test_proxy_reaches_real_qdrant_via_cache() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    cache = QdrantClientCache()
    proxy = BYOQdrantClientProxy(cache)

    real_client = await cache.get_or_create(url, None)
    token = current_qdrant_client.set(real_client)
    try:
        count = await ping(proxy)  # type: ignore[arg-type]
    finally:
        current_qdrant_client.reset(token)
        await cache.aclose_all()

    assert count >= 0
