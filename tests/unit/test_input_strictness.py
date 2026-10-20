"""A misspelled or mis-named key in a nested input must be an error, not a silent no-op.

Verified against a real Qdrant before the fix: a prefetch stage given Qdrant's own key
`filter` (instead of `query_filter`) returned unfiltered results, and
`{"mmr": {"candidate_limit": 5}}` ran MMR with its defaults without a word."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import GroupsResult, QueryResponse, UpdateResult, UpdateStatus

from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.registry import ToolRegistry

_STAGE = {"query_vector": [0.1, 0.2], "limit": 5}
_DISCOVER = {"target": 1, "context": [{"positive": 2, "negative": 3}]}


def _build() -> tuple[MCPServer[None], AsyncMock]:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(points=[])
    mock.query_points_groups.return_value = GroupsResult(groups=[])
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    mock.update_vectors.return_value = mock.upsert.return_value
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search", "payload"), read_only=False)
    client = cast(AsyncQdrantClient, mock)
    for module in (points_tools, query_tools, search_tools, vectors_tools):
        module.register(registry, client)
    return server, mock


# (tool, arguments with ONE bogus key somewhere nested, client method that must not run)
_CASES: list[tuple[str, dict[str, Any], str]] = [
    (
        "qdrant_query",
        {"prefetch": [{**_STAGE, "filter": {"must": []}}], "fusion": "rrf"},
        "query_points",
    ),
    ("qdrant_query", {"query_vector": [0.1], "mmr": {"candidate_limit": 5}}, "query_points"),
    (
        "qdrant_query",
        {"prefetch": [_STAGE, _STAGE], "fusion": {"method": "rrf", "weigths": [1, 2]}},
        "query_points",
    ),
    (
        "qdrant_query",
        {"prefetch": [_STAGE], "formula": {"expression": "$score", "default": {"a": 1}}},
        "query_points",
    ),
    (
        "qdrant_query",
        {"query_vector": [0.1], "lookup_from": {"collection": "o", "vectors": "dense"}},
        "query_points",
    ),
    (
        "qdrant_query",
        {"fusion": "rrf", "prefetch": [{"fusion": "rrf", "prefetch": [{**_STAGE, "bogus": 1}]}]},
        "query_points",
    ),
    (
        "qdrant_query_batch",
        {"queries": [{"query_vector": [0.1], "with_lookup": "x"}]},
        "query_batch_points",
    ),
    ("qdrant_recommend_batch", {"requests": [{"positive": [1], "nope": 1}]}, "query_batch_points"),
    ("qdrant_discover_batch", {"requests": [{**_DISCOVER, "nope": 1}]}, "query_batch_points"),
    (
        "qdrant_discover",
        {"target": 1, "context": [{"positive": 2, "negative": 3, "neutral": 4}]},
        "query_points",
    ),
    (
        "qdrant_points_upsert",
        {"points": [{"id": 1, "vector": [0.1], "payloads": {"a": 1}}]},  # `payloads`: a typo
        "upsert",
    ),
    (
        "qdrant_vectors_update",
        {"points": [{"id": 1, "vector": [0.1], "extra": 1}]},
        "update_vectors",
    ),
]


@pytest.mark.parametrize(("tool", "args", "method"), _CASES)
async def test_an_unknown_key_in_a_nested_input_is_an_error_not_a_silent_no_op(
    tool: str, args: dict[str, Any], method: str
) -> None:
    server, mock = _build()

    with pytest.raises(ToolError):
        await server.call_tool(tool, {"collection_name": "docs", **args})

    getattr(mock, method).assert_not_awaited()


async def test_the_same_inputs_without_the_unknown_key_are_accepted() -> None:
    server, mock = _build()

    await server.call_tool(
        "qdrant_query",
        {
            "collection_name": "docs",
            "prefetch": [
                {**_STAGE, "query_filter": {"must": [{"key": "c", "match": {"value": 1}}]}}
            ],
            "fusion": {"method": "rrf", "weights": [1], "k": 10},
            "mmr": None,
        },
    )
    await server.call_tool(
        "qdrant_points_upsert",
        {"collection_name": "docs", "points": [{"id": 1, "vector": [0.1], "payload": {"a": 1}}]},
    )

    mock.query_points.assert_awaited_once()
    mock.upsert.assert_awaited_once()


async def test_a_prefetch_stage_error_says_what_a_stage_needs_not_the_top_level_modes() -> None:
    server, mock = _build()

    with pytest.raises(ToolError) as excinfo:
        await server.call_tool(
            "qdrant_query",
            {"collection_name": "docs", "fusion": "rrf", "prefetch": [{"limit": 5}]},
        )

    message = str(excinfo.value)
    assert "prefetch stage needs exactly one of `query_vector` or `fusion`" in message
    assert "order_by" not in message and "sample" not in message  # modes a stage can't use
    mock.query_points.assert_not_awaited()
