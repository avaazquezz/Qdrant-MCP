"""Unit tests for the `search` toolset: mocked client, no real network.

Focused on the construction logic (mapping MCP-facing inputs to the right
Qdrant query-type objects), since that's the real risk area — the error
translation itself is generic (`call_qdrant`) and already covered by
`test_query_tool.py`; only two representative tools re-check it here.
"""

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
    DiscoverQuery,
    Fusion,
    FusionQuery,
    GroupsResult,
    PointGroup,
    QueryResponse,
    RecommendQuery,
    RecommendStrategy,
    ScoredPoint,
    SearchMatrixOffsetsResponse,
    SearchMatrixPair,
    SearchMatrixPairsResponse,
)

from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("search",), read_only=False)
    search_tools.register(registry, client)
    return server


async def test_query_batch_builds_one_request_per_query() -> None:
    mock = AsyncMock()
    mock.query_batch_points.return_value = [QueryResponse(points=[]), QueryResponse(points=[])]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_query_batch",
        {
            "collection_name": "docs",
            "queries": [
                {"query_vector": [0.1, 0.2], "limit": 5},
                {"query_vector": [0.3, 0.4], "limit": 3},
            ],
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_batch_points.call_args
    requests = kwargs["requests"]
    assert len(requests) == 2
    assert requests[0].query == [0.1, 0.2]
    assert requests[0].limit == 5
    assert requests[1].query == [0.3, 0.4]


async def test_query_groups_forwards_group_by_and_group_size() -> None:
    mock = AsyncMock()
    mock.query_points_groups.return_value = GroupsResult(
        groups=[PointGroup(id="doc-1", hits=[ScoredPoint(id=1, version=0, score=0.9)])]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_query_groups",
        {
            "collection_name": "docs",
            "group_by": "document_id",
            "query_vector": [0.1, 0.2],
            "group_size": 2,
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_points_groups.call_args
    assert kwargs["group_by"] == "document_id"
    assert kwargs["group_size"] == 2
    assert kwargs["query"] == [0.1, 0.2]


async def test_recommend_builds_recommend_query() -> None:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(points=[])
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_recommend",
        {
            "collection_name": "docs",
            "positive": [1, 2],
            "negative": [7],
            "strategy": "best_score",
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_points.call_args
    query = kwargs["query"]
    assert isinstance(query, RecommendQuery)
    assert query.recommend.positive == [1, 2]
    assert query.recommend.negative == [7]
    assert query.recommend.strategy == RecommendStrategy.BEST_SCORE


async def test_recommend_missing_positive_negative_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.query_points.side_effect = UnexpectedResponse(
        status_code=400,
        reason_phrase="Bad Request",
        content=b'{"status":{"error":"Bad request: negative or positive must be present"}}',
        headers=httpx.Headers({}),
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="must be present"):
        await server.call_tool("qdrant_recommend", {"collection_name": "docs"})


async def test_recommend_batch_builds_one_request_per_item() -> None:
    mock = AsyncMock()
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_recommend_batch",
        {"collection_name": "docs", "requests": [{"positive": [1], "negative": [7]}]},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_batch_points.call_args
    requests = kwargs["requests"]
    assert len(requests) == 1
    assert isinstance(requests[0].query, RecommendQuery)
    assert requests[0].query.recommend.positive == [1]


async def test_recommend_groups_forwards_group_by() -> None:
    mock = AsyncMock()
    mock.query_points_groups.return_value = GroupsResult(groups=[])
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_recommend_groups",
        {"collection_name": "docs", "group_by": "document_id", "positive": [1, 2]},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_points_groups.call_args
    assert kwargs["group_by"] == "document_id"
    assert isinstance(kwargs["query"], RecommendQuery)


async def test_discover_builds_discover_query() -> None:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(points=[])
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_discover",
        {"collection_name": "docs", "target": 1, "context": [{"positive": 2, "negative": 7}]},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_points.call_args
    query = kwargs["query"]
    assert isinstance(query, DiscoverQuery)
    context = query.discover.context
    assert isinstance(context, list)
    assert query.discover.target == 1
    assert context[0].positive == 2
    assert context[0].negative == 7


async def test_discover_batch_builds_one_request_per_item() -> None:
    mock = AsyncMock()
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_discover_batch",
        {
            "collection_name": "docs",
            "requests": [{"target": 1, "context": [{"positive": 2, "negative": 7}]}],
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.query_batch_points.call_args
    requests = kwargs["requests"]
    assert len(requests) == 1
    assert isinstance(requests[0].query, DiscoverQuery)


async def test_distance_matrix_pairs_forwards_sample_and_limit() -> None:
    mock = AsyncMock()
    mock.search_matrix_pairs.return_value = SearchMatrixPairsResponse(
        pairs=[SearchMatrixPair(a=1, b=2, score=0.5)]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_distance_matrix_pairs", {"collection_name": "docs", "sample": 20, "limit": 5}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.search_matrix_pairs.call_args
    assert kwargs["sample"] == 20
    assert kwargs["limit"] == 5


async def test_distance_matrix_pairs_missing_collection_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.search_matrix_pairs.side_effect = UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=b'{"status":{"error":"Not found: Collection `docs` doesn\'t exist!"}}',
        headers=httpx.Headers({}),
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool("qdrant_distance_matrix_pairs", {"collection_name": "docs"})


async def test_distance_matrix_offsets_forwards_sample_and_limit() -> None:
    mock = AsyncMock()
    mock.search_matrix_offsets.return_value = SearchMatrixOffsetsResponse(
        offsets_row=[0], offsets_col=[1], scores=[0.5], ids=[1, 2]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_distance_matrix_offsets", {"collection_name": "docs", "sample": 15, "limit": 4}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.search_matrix_offsets.call_args
    assert kwargs["sample"] == 15
    assert kwargs["limit"] == 4


async def test_query_batch_hybrid_fusion_item_builds_fusion_query() -> None:
    mock = AsyncMock()
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    server = _build(cast(AsyncQdrantClient, mock))

    await server.call_tool(
        "qdrant_query_batch",
        {
            "collection_name": "docs",
            "queries": [
                {
                    "fusion": "dbsf",
                    "prefetch": [
                        {"query_vector": [0.1, 0.2], "using": "dense"},
                        {"query_vector": [0.3, 0.4], "using": "sparse"},
                    ],
                }
            ],
        },
    )

    _, kwargs = mock.query_batch_points.call_args
    request = kwargs["requests"][0]
    assert isinstance(request.query, FusionQuery)
    assert request.query.fusion == Fusion.DBSF
    assert request.prefetch is not None
    assert len(request.prefetch) == 2
