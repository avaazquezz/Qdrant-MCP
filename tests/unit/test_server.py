"""Confirms build_server wires Settings -> client -> registry -> tools, no network touched."""

from __future__ import annotations

import pytest

from mcp_qdrant.config import Settings
from mcp_qdrant.qdrant_client_cache import QdrantClientCache
from mcp_qdrant.server import build_server


async def test_build_server_registers_default_toolset() -> None:
    server = build_server(Settings.from_env({}))
    tools = await server.list_tools()
    assert "qdrant_health_check" in [t.name for t in tools]
    assert "qdrant_collection_create" in [t.name for t in tools]
    assert "qdrant_query" in [t.name for t in tools]
    assert len(tools) == 13


async def test_build_server_respects_disabled_toolsets() -> None:
    server = build_server(Settings.from_env({"QDRANT_MCP_TOOLSETS": "search"}))
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert "qdrant_health_check" not in names
    assert "qdrant_query" not in names
    assert "qdrant_query_batch" in names
    assert len(tools) == 9


async def test_build_server_in_byo_mode_uses_proxy_client() -> None:
    settings = Settings.from_env({"QDRANT_MCP_BYO": "1", "QDRANT_MCP_TRANSPORT": "streamable-http"})
    cache = QdrantClientCache()
    server = build_server(settings, qdrant_client_cache=cache)
    tools = await server.list_tools()
    assert "qdrant_health_check" in [t.name for t in tools]
    await cache.aclose_all()


def test_build_server_in_byo_mode_requires_a_cache() -> None:
    settings = Settings.from_env({"QDRANT_MCP_BYO": "1", "QDRANT_MCP_TRANSPORT": "streamable-http"})
    with pytest.raises(AssertionError):
        build_server(settings, qdrant_client_cache=None)
