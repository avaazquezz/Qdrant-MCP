"""Every query_points-based tool takes the same tuning parameters and the
`qdrant_query` family takes the same query modes: mocked client, no network."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Direction,
    FormulaQuery,
    Fusion,
    FusionQuery,
    GroupsResult,
    Mmr,
    NearestQuery,
    OrderBy,
    OrderByQuery,
    QueryResponse,
    ReadConsistencyType,
    Rrf,
    RrfQuery,
    SampleQuery,
    SearchParams,
    SparseVector,
)

from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

_DISCOVER = {"target": 1, "context": [{"positive": 2, "negative": 3}]}

# (tool, minimal arguments, client method it ends up calling, whether it pages with `offset`)
_SINGLE_TOOLS = [
    ("qdrant_query", {"query_vector": [0.1, 0.2]}, "query_points", True),
    ("qdrant_recommend", {"positive": [1]}, "query_points", True),
    ("qdrant_discover", _DISCOVER, "query_points", True),
    (
        "qdrant_query_groups",
        {"group_by": "doc", "query_vector": [0.1]},
        "query_points_groups",
        False,
    ),
    ("qdrant_recommend_groups", {"group_by": "doc", "positive": [1]}, "query_points_groups", False),
]
# (tool, the list argument holding the items, one minimal item)
_BATCH_TOOLS = [
    ("qdrant_query_batch", "queries", {"query_vector": [0.1, 0.2]}),
    ("qdrant_recommend_batch", "requests", {"positive": [1]}),
    ("qdrant_discover_batch", "requests", _DISCOVER),
]

_TUNING = {
    "search_params": {"exact": True, "hnsw_ef": 64},
    "score_threshold": 0.4,
    "timeout_seconds": 5,
    "consistency": "majority",
}


def _build(mock: AsyncMock) -> MCPServer[None]:
    mock.query_points.return_value = QueryResponse(points=[])
    mock.query_points_groups.return_value = GroupsResult(groups=[])
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search"), read_only=False)
    query_tools.register(registry, cast(AsyncQdrantClient, mock))
    search_tools.register(registry, cast(AsyncQdrantClient, mock))
    return server


async def _call(server: MCPServer[None], tool: str, **args: Any) -> CallToolResult:
    result = await server.call_tool(tool, {"collection_name": "docs", **args})
    assert isinstance(result, CallToolResult)
    return result


@pytest.mark.parametrize(("tool", "base", "method", "pages"), _SINGLE_TOOLS)
async def test_tuning_parameters_reach_the_client(
    tool: str, base: dict[str, Any], method: str, pages: bool
) -> None:
    mock = AsyncMock()
    server = _build(mock)
    extra = {"offset": 3} if pages else {}

    await _call(server, tool, **base, **_TUNING, **extra)

    _, kwargs = getattr(mock, method).call_args
    assert kwargs["search_params"] == SearchParams(exact=True, hnsw_ef=64)
    assert kwargs["score_threshold"] == 0.4
    assert kwargs["timeout"] == 5
    assert kwargs["consistency"] == ReadConsistencyType.MAJORITY
    if pages:
        assert kwargs["offset"] == 3


@pytest.mark.parametrize(("tool", "base", "method", "pages"), _SINGLE_TOOLS)
async def test_tuning_parameters_default_to_unset(
    tool: str, base: dict[str, Any], method: str, pages: bool
) -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(server, tool, **base)

    _, kwargs = getattr(mock, method).call_args
    for name in ("search_params", "score_threshold", "timeout", "consistency"):
        assert kwargs[name] is None, name
    if pages:
        assert kwargs["offset"] is None


@pytest.mark.parametrize(("tool", "base", "_method", "pages"), _SINGLE_TOOLS)
async def test_a_replica_count_is_accepted_for_consistency(
    tool: str, base: dict[str, Any], _method: str, pages: bool
) -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(server, tool, **base, consistency=2)

    _, kwargs = getattr(mock, _method).call_args
    assert kwargs["consistency"] == 2


@pytest.mark.parametrize(("tool", "items_arg", "item"), _BATCH_TOOLS)
async def test_batch_items_take_per_item_tuning_and_the_batch_takes_timeout_and_consistency(
    tool: str, items_arg: str, item: dict[str, Any]
) -> None:
    mock = AsyncMock()
    server = _build(mock)
    tuned_item = {
        **item,
        "search_params": {"exact": True},
        "score_threshold": 0.4,
        "offset": 3,
    }

    await _call(server, tool, **{items_arg: [tuned_item]}, timeout_seconds=7, consistency="quorum")

    _, kwargs = mock.query_batch_points.call_args
    (request,) = kwargs["requests"]
    assert request.params == SearchParams(exact=True)
    assert request.score_threshold == 0.4
    assert request.offset == 3
    assert kwargs["timeout"] == 7
    assert kwargs["consistency"] == ReadConsistencyType.QUORUM


@pytest.mark.parametrize(
    "bad",
    [
        {"offset": -1},
        {"timeout_seconds": 0},
        {"consistency": 0},
        {"consistency": "bogus"},
        {"score_threshold": "high"},
        {"search_params": {"hnsw_ef": "wide"}},
    ],
)
async def test_out_of_range_tuning_is_rejected_before_calling_qdrant(bad: dict[str, Any]) -> None:
    mock = AsyncMock()
    server = _build(mock)

    with pytest.raises(ToolError):
        await _call(server, "qdrant_query", query_vector=[0.1], **bad)
    mock.query_points.assert_not_awaited()


# --- query modes through the tools --------------------------------------------------


async def test_query_mmr_builds_a_nearest_query_with_mmr() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(
        server,
        "qdrant_query",
        query_vector=[0.1, 0.2],
        mmr={"diversity": 0.5, "candidates_limit": 30},
    )

    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == NearestQuery(
        nearest=[0.1, 0.2], mmr=Mmr(diversity=0.5, candidates_limit=30)
    )


async def test_query_formula_over_a_prefetch_stage() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(
        server,
        "qdrant_query",
        prefetch=[{"query_vector": [0.1, 0.2], "limit": 50}],
        formula={
            "expression": {"sum": ["$score", {"mult": [0.5, "popularity"]}]},
            "defaults": {"popularity": 0.0},
        },
    )

    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], FormulaQuery)
    assert kwargs["query"].defaults == {"popularity": 0.0}
    assert kwargs["prefetch"][0].limit == 50


async def test_query_invalid_formula_is_a_tool_error_not_a_crash() -> None:
    mock = AsyncMock()
    server = _build(mock)

    with pytest.raises(ToolError, match="not a valid formula expression"):
        await _call(
            server,
            "qdrant_query",
            prefetch=[{"query_vector": [0.1], "limit": 5}],
            formula={"expression": {"bogus": 1}},
        )
    mock.query_points.assert_not_awaited()


async def test_query_order_by_accepts_a_key_or_a_spec() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(server, "qdrant_query", order_by="price")
    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == OrderByQuery(order_by="price")

    await _call(
        server,
        "qdrant_query",
        order_by={"key": "price", "direction": "desc", "start_from": 25},
    )
    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == OrderByQuery(
        order_by=OrderBy(key="price", direction=Direction.DESC, start_from=25)
    )


async def test_query_sample_random() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(server, "qdrant_query", sample="random", limit=3)

    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], SampleQuery)
    assert kwargs["limit"] == 3


async def test_query_rejects_an_unknown_sample_strategy() -> None:
    mock = AsyncMock()
    server = _build(mock)

    with pytest.raises(ToolError):
        await _call(server, "qdrant_query", sample="stratified")
    mock.query_points.assert_not_awaited()


async def test_query_weighted_rrf_and_plain_fusion_names_both_work() -> None:
    mock = AsyncMock()
    server = _build(mock)
    stages = [{"query_vector": [0.1, 0.2], "using": "dense"}, {"query_vector": [0.3], "using": "x"}]

    await _call(
        server,
        "qdrant_query",
        prefetch=stages,
        fusion={"method": "rrf", "weights": [2, 1], "k": 20},
    )
    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == RrfQuery(rrf=Rrf(k=20, weights=[2.0, 1.0]))

    await _call(server, "qdrant_query", prefetch=stages, fusion="dbsf")
    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], FusionQuery)


async def test_query_nested_prefetch_with_a_sparse_stage_reaches_the_client() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(
        server,
        "qdrant_query",
        query_vector=[[1.0, 0.0], [0.0, 1.0]],
        using="colbert",
        prefetch=[
            {
                "fusion": "rrf",
                "limit": 50,
                "prefetch": [
                    {"query_vector": [0.1, 0.2], "using": "dense", "limit": 100},
                    {
                        "query_vector": {"indices": [1], "values": [1.0]},
                        "using": "sparse",
                        "limit": 100,
                        "score_threshold": 0.1,
                    },
                ],
            }
        ],
    )

    _, kwargs = mock.query_points.call_args
    (stage,) = kwargs["prefetch"]
    assert stage.query == FusionQuery(fusion=Fusion.RRF)
    assert [p.using for p in stage.prefetch] == ["dense", "sparse"]
    assert stage.prefetch[1].query == SparseVector(indices=[1], values=[1.0])
    assert stage.prefetch[1].score_threshold == 0.1
    assert kwargs["query"] == [[1.0, 0.0], [0.0, 1.0]]


async def test_query_rejects_two_modes_and_mmr_without_a_vector() -> None:
    mock = AsyncMock()
    server = _build(mock)

    with pytest.raises(ToolError, match="exactly one of"):
        await _call(server, "qdrant_query", query_vector=[0.1], sample="random")
    with pytest.raises(ToolError, match="`mmr` only applies"):
        await _call(server, "qdrant_query", sample="random", mmr={"diversity": 0.5})
    with pytest.raises(ToolError):
        await _call(server, "qdrant_query", query_vector=[0.1], mmr={"diversity": 2})
    mock.query_points.assert_not_awaited()


async def test_batch_and_groups_take_the_new_query_modes_too() -> None:
    mock = AsyncMock()
    server = _build(mock)

    await _call(
        server,
        "qdrant_query_batch",
        queries=[{"order_by": "price"}, {"sample": "random"}, {"query_vector": [0.1], "mmr": {}}],
    )
    _, kwargs = mock.query_batch_points.call_args
    queries = [r.query for r in kwargs["requests"]]
    assert queries[0] == OrderByQuery(order_by="price")
    assert isinstance(queries[1], SampleQuery)
    assert queries[2] == NearestQuery(nearest=[0.1], mmr=Mmr())

    await _call(server, "qdrant_query_groups", group_by="doc", order_by="price")
    _, kwargs = mock.query_points_groups.call_args
    assert kwargs["query"] == OrderByQuery(order_by="price")
