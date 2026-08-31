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
from qdrant_client.http.models import (
    Fusion,
    FusionQuery,
    LookupLocation,
    QueryResponse,
    ScoredPoint,
)

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


async def test_query_hybrid_fusion_builds_fusion_query_with_prefetch() -> None:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(
        points=[ScoredPoint(id=1, version=0, score=0.9, payload={"city": "ny"})]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_query",
        {
            "collection_name": "docs",
            "fusion": "rrf",
            "prefetch": [
                {"query_vector": [0.1, 0.2, 0.3, 0.4], "using": "dense", "limit": 20},
                {"query_vector": [0.5, 0.5], "using": "sparse", "limit": 20},
            ],
            "limit": 5,
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], FusionQuery)
    assert kwargs["query"].fusion == Fusion.RRF
    assert kwargs["prefetch"] is not None
    assert [p.using for p in kwargs["prefetch"]] == ["dense", "sparse"]


async def test_query_using_and_lookup_from_are_forwarded() -> None:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(points=[])
    server = _build(cast(AsyncQdrantClient, mock))

    await server.call_tool(
        "qdrant_query",
        {
            "collection_name": "docs",
            "query_vector": 1,
            "using": "dense",
            "lookup_from": {"collection": "other", "vector": "dense"},
        },
    )

    _, kwargs = mock.query_points.call_args
    assert kwargs["using"] == "dense"
    assert kwargs["lookup_from"] == LookupLocation(collection="other", vector="dense")


async def test_query_neither_vector_nor_fusion_raises_tool_error() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="exactly one of"):
        await server.call_tool("qdrant_query", {"collection_name": "docs"})


async def test_query_both_vector_and_fusion_raises_tool_error() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="exactly one of"):
        await server.call_tool(
            "qdrant_query",
            {"collection_name": "docs", "query_vector": [0.1, 0.2], "fusion": "rrf"},
        )
