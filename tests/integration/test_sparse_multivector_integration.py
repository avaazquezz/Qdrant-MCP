"""Confirms sparse/multivector writes and queries, and conditional upserts, work
end to end against a real Qdrant — the unit tests only prove the schema accepts
these shapes, not that Qdrant does what the tool docstrings promise."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    ExtendedPointId,
    MultiVectorComparator,
    MultiVectorConfig,
    QueryResponse,
    SparseVectorParams,
    VectorParams,
)

from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

_SPARSE_QUERY = {"indices": [1, 2], "values": [1.0, 1.0]}
_MULTI_QUERY = [[1.0, 0.0], [0.0, 1.0]]

# Three points whose dense, sparse and multivector representations all rank
# point 1 first for the queries above, and point 3 last on sparse.
_POINTS = [
    {
        "id": 1,
        "vector": {
            "dense": [1.0, 0.0, 0.0, 0.0],
            "sparse": {"indices": [1, 2], "values": [1.0, 0.5]},
            "colbert": [[1.0, 0.0], [0.0, 1.0]],
        },
        "payload": {"rank": 1},
    },
    {
        "id": 2,
        "vector": {
            "dense": [0.0, 1.0, 0.0, 0.0],
            "sparse": {"indices": [2, 3], "values": [1.0, 0.5]},
            "colbert": [[0.0, 1.0], [1.0, 1.0]],
        },
        "payload": {"rank": 2},
    },
    {
        "id": 3,
        "vector": {
            "dense": [0.0, 0.0, 1.0, 0.0],
            "sparse": {"indices": [3, 4], "values": [1.0, 0.5]},
            "colbert": [[1.0, 1.0], [1.0, 0.0]],
        },
        "payload": {"rank": 3},
    },
]


@pytest.fixture
async def env() -> AsyncIterator[tuple[MCPServer[None], str]]:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search"), read_only=False)
    points_tools.register(registry, client)
    query_tools.register(registry, client)
    search_tools.register(registry, client)

    await client.create_collection(
        name,
        vectors_config={
            "dense": VectorParams(size=4, distance=Distance.COSINE),
            "colbert": VectorParams(
                size=2,
                distance=Distance.COSINE,
                multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM),
            ),
        },
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )
    try:
        yield server, name
    finally:
        await client.delete_collection(name)
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> CallToolResult:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    return result


def _ids(result: CallToolResult) -> list[ExtendedPointId]:
    return [p.id for p in QueryResponse.model_validate(result.structured_content).points]


async def _seed(server: MCPServer[None], name: str) -> None:
    await _call(server, "qdrant_points_upsert", {"collection_name": name, "points": _POINTS})


async def _payload_of(server: MCPServer[None], name: str, point_id: int) -> dict[str, Any] | None:
    result = await _call(server, "qdrant_points_get", {"collection_name": name, "ids": [point_id]})
    assert result.structured_content is not None
    points = result.structured_content["points"]
    return points[0]["payload"] if points else None


async def test_named_sparse_and_multivector_points_are_writable_and_queryable(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    sparse = await _call(
        server,
        "qdrant_query",
        {"collection_name": name, "query_vector": _SPARSE_QUERY, "using": "sparse"},
    )
    assert _ids(sparse)[0] == 1

    multi = await _call(
        server,
        "qdrant_query",
        {"collection_name": name, "query_vector": _MULTI_QUERY, "using": "colbert"},
    )
    assert _ids(multi)[0] == 1


async def test_hybrid_rrf_over_dense_and_sparse_prefetch(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    hybrid = await _call(
        server,
        "qdrant_query",
        {
            "collection_name": name,
            "fusion": "rrf",
            "prefetch": [
                {"query_vector": [1.0, 0.0, 0.0, 0.0], "using": "dense", "limit": 3},
                {"query_vector": _SPARSE_QUERY, "using": "sparse", "limit": 3},
            ],
            "limit": 3,
        },
    )
    ids = _ids(hybrid)
    assert ids[0] == 1
    assert set(ids) == {1, 2, 3}


async def test_sparse_prefetch_reranked_by_multivector(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    reranked = await _call(
        server,
        "qdrant_query",
        {
            "collection_name": name,
            "query_vector": _MULTI_QUERY,
            "using": "colbert",
            "prefetch": [{"query_vector": _SPARSE_QUERY, "using": "sparse", "limit": 2}],
            "limit": 2,
        },
    )
    # Point 3 shares no sparse index with the query, so the prefetch stage drops it.
    assert 3 not in _ids(reranked)
    assert _ids(reranked)[0] == 1


async def test_recommend_with_sparse_example(env: tuple[MCPServer[None], str]) -> None:
    server, name = env
    await _seed(server, name)

    recommended = await _call(
        server,
        "qdrant_recommend",
        {"collection_name": name, "positive": [_SPARSE_QUERY], "using": "sparse"},
    )
    assert _ids(recommended)[0] == 1


async def test_upsert_update_mode_insert_only_never_overwrites(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    await _call(
        server,
        "qdrant_points_upsert",
        {
            "collection_name": name,
            "update_mode": "insert_only",
            "points": [
                {"id": 1, "vector": _POINTS[0]["vector"], "payload": {"rank": "OVERWRITTEN"}},
                {"id": 4, "vector": _POINTS[0]["vector"], "payload": {"rank": 4}},
            ],
        },
    )

    assert await _payload_of(server, name, 1) == {"rank": 1}
    assert await _payload_of(server, name, 4) == {"rank": 4}


async def test_upsert_update_mode_update_only_never_creates(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    await _call(
        server,
        "qdrant_points_upsert",
        {
            "collection_name": name,
            "update_mode": "update_only",
            "points": [
                {"id": 1, "vector": _POINTS[0]["vector"], "payload": {"rank": "UPDATED"}},
                {"id": 99, "vector": _POINTS[0]["vector"], "payload": {"rank": 99}},
            ],
        },
    )

    assert await _payload_of(server, name, 1) == {"rank": "UPDATED"}
    assert await _payload_of(server, name, 99) is None


async def test_upsert_update_filter_only_overwrites_matching_points(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    await _seed(server, name)

    def upsert_args(match_rank: int) -> dict[str, Any]:
        return {
            "collection_name": name,
            "update_filter": {"must": [{"key": "rank", "match": {"value": match_rank}}]},
            "points": [{"id": 1, "vector": _POINTS[0]["vector"], "payload": {"rank": "FILTERED"}}],
        }

    await _call(server, "qdrant_points_upsert", upsert_args(match_rank=999))
    assert await _payload_of(server, name, 1) == {"rank": 1}

    await _call(server, "qdrant_points_upsert", upsert_args(match_rank=1))
    assert await _payload_of(server, name, 1) == {"rank": "FILTERED"}
