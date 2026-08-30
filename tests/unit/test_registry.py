"""Unit tests for the toolset filter and the read-only guardrail."""

from __future__ import annotations

from mcp.server import MCPServer
from mcp_types import ToolAnnotations

from mcp_qdrant.tools.registry import ToolRegistry

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False)


async def noop_tool() -> str:
    return "ok"


async def test_disabled_toolset_is_never_registered() -> None:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    registry.register(noop_tool, toolset="search", annotations=READ_ONLY)
    assert await server.list_tools() == []


async def test_enabled_toolset_is_registered() -> None:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    registry.register(noop_tool, toolset="core", annotations=READ_ONLY)
    assert [t.name for t in await server.list_tools()] == ["noop_tool"]


async def test_read_only_blocks_destructive_tool() -> None:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=True)
    registry.register(noop_tool, toolset="core", annotations=DESTRUCTIVE)
    assert await server.list_tools() == []


async def test_read_only_allows_non_destructive_tool() -> None:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=True)
    registry.register(noop_tool, toolset="core", annotations=READ_ONLY)
    assert [t.name for t in await server.list_tools()] == ["noop_tool"]


async def test_read_only_blocks_non_destructive_mutation() -> None:
    """A tool that mutates but isn't destructive (e.g. collection_create) must
    still be blocked: QDRANT_MCP_READ_ONLY means no writes, not just no deletes."""
    mutating_non_destructive = ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False
    )
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=True)
    registry.register(noop_tool, toolset="core", annotations=mutating_non_destructive)
    assert await server.list_tools() == []
