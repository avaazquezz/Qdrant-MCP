"""Unit tests for qdrant_query: mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import QueryResponse, ScoredPoint

from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    query_tools.register(registry, client)
    return server


async def test_query_returns_scored_points() -> None:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(
        points=[ScoredPoint(id=1, version=0, score=0.9, payload={"city": "ny"})]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_query",
        {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 5},
    )
    assert isinstance(result, CallToolResult)
    payload = QueryResponse.model_validate(result.structured_content)
    assert payload.points[0].score == 0.9
    mock.query_points.assert_awaited_once()


async def test_query_missing_collection_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.query_points.side_effect = UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=b'{"status":{"error":"Not found: Collection `docs` doesn\'t exist!"}}',
        headers=httpx.Headers({}),
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_query", {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4]}
        )
