"""Confirms qdrant_health_check really reaches a live Qdrant instance."""

from __future__ import annotations

import os

import pytest
from qdrant_client import AsyncQdrantClient

from mcp_qdrant.qdrant_client import ping

pytestmark = pytest.mark.integration


async def test_ping_reaches_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    try:
        count = await ping(client)
    finally:
        await client.close()
    assert count >= 0
