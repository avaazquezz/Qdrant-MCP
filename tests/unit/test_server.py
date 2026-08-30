"""Confirms build_server wires Settings -> client -> registry -> tools, no network touched."""

from __future__ import annotations

from mcp_qdrant.config import Settings
from mcp_qdrant.server import build_server


async def test_build_server_registers_default_toolset() -> None:
    server = build_server(Settings.from_env({}))
    tools = await server.list_tools()
    assert [t.name for t in tools] == ["qdrant_health_check"]


async def test_build_server_respects_disabled_toolsets() -> None:
    server = build_server(Settings.from_env({"QDRANT_MCP_TOOLSETS": "search"}))
    tools = await server.list_tools()
    assert tools == []
