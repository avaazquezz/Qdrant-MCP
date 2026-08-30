"""Unit tests for the qdrant_health_check tool: mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from mcp_qdrant.tools import core as core_tools
from mcp_qdrant.tools.core import HealthCheckResult
from mcp_qdrant.tools.registry import ToolRegistry


async def test_health_check_reports_ok_on_success() -> None:
    mock = AsyncMock()
    mock.get_collections.return_value = AsyncMock(collections=[AsyncMock()])
    client = cast(AsyncQdrantClient, mock)

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    core_tools.register(registry, client)

    result = await server.call_tool("qdrant_health_check", {})
    assert isinstance(result, CallToolResult)
    payload = HealthCheckResult.model_validate(result.structured_content)
    assert payload.ok is True
    assert payload.collection_count == 1
    assert payload.error is None


async def test_health_check_reports_error_without_raising() -> None:
    mock = AsyncMock()
    mock.get_collections.side_effect = ResponseHandlingException(ConnectionError("refused"))
    client = cast(AsyncQdrantClient, mock)

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    core_tools.register(registry, client)

    result = await server.call_tool("qdrant_health_check", {})
    assert isinstance(result, CallToolResult)
    payload = HealthCheckResult.model_validate(result.structured_content)
    assert payload.ok is False
    assert payload.error is not None
