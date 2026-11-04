"""Unit tests for `qdrant_search_quality_eval` (Fase 20): vector selection, recall@k against
the exact search with the query point left out, and the percentile it reports."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionConfig,
    CollectionInfo,
    CollectionParams,
    CollectionStatus,
    Distance,
    HnswConfig,
    OptimizersConfig,
    OptimizersStatusOneOf,
    QueryResponse,
    ScoredPoint,
    SearchParams,
    SparseVectorParams,
    VectorParams,
)

from mcp_qdrant.tools import quality
from mcp_qdrant.tools.quality import SearchQualityReport
from mcp_qdrant.tools.registry import ToolRegistry


def _info(vectors: Any, sparse: Any = None, indexed: int = 100) -> CollectionInfo:
    return CollectionInfo(
        status=CollectionStatus.GREEN,
        optimizer_status=OptimizersStatusOneOf.OK,
        segments_count=1,
        points_count=100,
        indexed_vectors_count=indexed,
        config=CollectionConfig(
            params=CollectionParams(vectors=vectors, sparse_vectors=sparse),
            hnsw_config=HnswConfig(m=16, ef_construct=100, full_scan_threshold=10000),
            optimizer_config=OptimizersConfig(default_segment_number=0, flush_interval_sec=5),
        ),
        payload_schema={},
    )


def _hits(*ids: int) -> QueryResponse:
    return QueryResponse(points=[ScoredPoint(id=i, version=1, score=1.0) for i in ids])


def _client(
    info: CollectionInfo, exact: list[int], approx: list[int], sample: int = 1
) -> AsyncMock:
    """Point 0 (vector [1, 0]) is the sampled query; searches answer `exact` or `approx`
    depending on `search_params.exact`."""

    async def query_points(collection: str, **kwargs: Any) -> QueryResponse:
        if kwargs.get("search_params") is None:  # the sampling call
            points = [
                ScoredPoint(id=i, version=1, score=0.0, vector=[1.0, 0.0]) for i in range(sample)
            ]
            return QueryResponse(points=points)
        params = cast(SearchParams, kwargs["search_params"])
        return _hits(*(exact if params.exact else approx))

    mock = AsyncMock()
    mock.get_collection.return_value = info
    mock.query_points.side_effect = query_points
    return mock


def _server(mock: AsyncMock) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("admin",), read_only=False)
    quality.register(registry, cast(AsyncQdrantClient, mock))
    return server


async def _report(mock: AsyncMock, **args: Any) -> SearchQualityReport:
    result = await _server(mock).call_tool(
        "qdrant_search_quality_eval", {"collection_name": "docs", **args}
    )
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return SearchQualityReport.model_validate(result.structured_content)


UNNAMED = VectorParams(size=2, distance=Distance.COSINE)


async def test_recall_counts_the_exact_neighbours_the_approximate_search_also_found() -> None:
    # Both lists include the query point 0 itself, which must not count either way.
    mock = _client(_info(UNNAMED), exact=[0, 1, 2, 3], approx=[0, 1, 9, 3])
    report = await _report(mock, limit=3)
    [variant] = report.variants
    assert variant.recall_mean == variant.recall_min == round(2 / 3, 3)
    assert variant.search_params == {}  # the collection's own settings, echoed as given
    # limit + 1 asked for, so the self-hit can be dropped — and no filter, which would switch
    # Qdrant to its filtered-search path.
    for call in mock.query_points.call_args_list[1:]:
        assert call.kwargs["limit"] == 4 and "query_filter" not in call.kwargs


async def test_the_self_hit_missing_still_leaves_limit_results() -> None:
    mock = _client(_info(UNNAMED), exact=[1, 2, 3, 4], approx=[1, 2, 3, 4])
    report = await _report(mock, limit=3)
    assert report.variants[0].recall_mean == 1.0  # 4th result dropped, not compared


async def test_each_variant_is_measured_against_the_same_truth() -> None:
    mock = _client(_info(UNNAMED), exact=[0, 1, 2], approx=[0, 5, 6])
    report = await _report(mock, limit=2, variants=[{"hnsw_ef": 8}, {"exact": True}])
    assert [v.search_params for v in report.variants] == [{"hnsw_ef": 8}, {"exact": True}]
    assert [v.recall_mean for v in report.variants] == [0.0, 1.0]


async def test_recall_is_null_when_there_is_nothing_else_to_find() -> None:
    mock = _client(_info(UNNAMED), exact=[0], approx=[0])
    report = await _report(mock)
    assert report.variants[0].recall_mean is None
    assert any("recall is undefined" in note for note in report.notes)


async def test_an_unindexed_collection_says_recall_is_exact_by_construction() -> None:
    mock = _client(_info(UNNAMED, indexed=0), exact=[0, 1], approx=[0, 1])
    report = await _report(mock)
    assert any("1.0 by construction" in note for note in report.notes)


async def test_the_only_named_vector_is_picked_and_sampled_by_name() -> None:
    mock = _client(_info({"dense": UNNAMED}), exact=[0, 1], approx=[0, 1])

    async def query_points(collection: str, **kwargs: Any) -> QueryResponse:
        if kwargs.get("search_params") is None:
            assert kwargs["with_vectors"] == ["dense"]
            return QueryResponse(
                points=[ScoredPoint(id=0, version=1, score=0.0, vector={"dense": [1.0, 0.0]})]
            )
        assert kwargs["using"] == "dense"
        return _hits(0, 1)

    mock.query_points.side_effect = query_points
    report = await _report(mock)
    assert report.using == "dense" and report.queries == 1


@pytest.mark.parametrize(
    ("info", "using", "error"),
    [
        (_info(UNNAMED), "dense", "single unnamed vector; omit `using`"),
        (_info({"a": UNNAMED, "b": UNNAMED}), None, r"several vectors \(\['a', 'b'\]\)"),
        (_info({"a": UNNAMED}), "nope", "has no dense vector 'nope'"),
        (_info({"a": UNNAMED}, sparse={"s": SparseVectorParams()}), "s", "sparse search is always"),
    ],
)
async def test_vector_selection_fails_clearly(info: CollectionInfo, using: Any, error: str) -> None:
    mock = _client(info, exact=[], approx=[])
    args: dict[str, Any] = {"collection_name": "docs"} | ({"using": using} if using else {})
    with pytest.raises(ToolError, match=error):
        await _server(mock).call_tool("qdrant_search_quality_eval", args)
    mock.query_points.assert_not_called()


async def test_a_collection_without_sampled_vectors_is_refused() -> None:
    mock = _client(_info(UNNAMED), exact=[], approx=[], sample=0)
    with pytest.raises(ToolError, match="no points with this vector"):
        await _server(mock).call_tool("qdrant_search_quality_eval", {"collection_name": "docs"})


def test_p95_is_the_nearest_rank_observed_value() -> None:
    assert quality._p95([0.005]) == 0.005
    assert quality._p95([float(i) for i in range(1, 21)]) == 19.0
    assert quality._p95([float(i) for i in range(1, 101)]) == 95.0


async def test_an_explicit_vector_is_used_among_several() -> None:
    mock = _client(_info({"a": UNNAMED, "b": UNNAMED}), exact=[0, 1], approx=[0, 1])

    async def query_points(collection: str, **kwargs: Any) -> QueryResponse:
        assert kwargs["using"] == "b"
        if kwargs.get("search_params") is None:
            return QueryResponse(
                points=[ScoredPoint(id=0, version=1, score=0.0, vector={"b": [1.0, 0.0]})]
            )
        return _hits(0, 1)

    mock.query_points.side_effect = query_points
    assert (await _report(mock, using="b")).using == "b"
