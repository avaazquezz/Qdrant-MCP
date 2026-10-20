"""Confirms every query mode and tuning parameter of the `qdrant_query` family
works against a real Qdrant, and that the documented behaviors (formula needs a
prefetch, `order_by` needs a range index, weights follow stage order, scroll
paging with `order_by`) are what Qdrant actually does."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    MultiVectorComparator,
    MultiVectorConfig,
    PayloadSchemaType,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

# id: (dense, colbert, city, price, date). Points 1-3 are near-duplicates of each
# other on `dense`; 4 is orthogonal; 5 sits in between.
_ROWS = {
    1: ([1.0, 0.0], [[1.0, 0.0]], "ny", 10.0, "2026-01-01T00:00:00Z"),
    2: ([1.0, 0.01], [[0.9, 0.1]], "ny", 20.0, "2025-06-01T00:00:00Z"),
    3: ([1.0, 0.02], [[0.1, 0.9]], "sf", 30.0, "2026-01-02T00:00:00Z"),
    4: ([0.0, 1.0], [[0.0, 1.0]], "sf", 40.0, "2024-01-01T00:00:00Z"),
    5: ([0.5, 0.5], [[0.7, 0.7]], "ny", 50.0, "2026-01-03T00:00:00Z"),
}
_DENSE_QUERY = [1.0, 0.0]


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
            "dense": VectorParams(size=2, distance=Distance.COSINE),
            "colbert": VectorParams(
                size=2,
                distance=Distance.COSINE,
                multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM),
            ),
        },
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )
    await client.upsert(
        name,
        points=[
            PointStruct(
                id=point_id,
                vector={
                    "dense": dense,
                    "colbert": colbert,
                    # Sparse score against {1: 1.0} is the point id, so 5 ranks first.
                    "sparse": SparseVector(indices=[1], values=[float(point_id)]),
                },
                payload={"city": city, "price": price, "date": date},
            )
            for point_id, (dense, colbert, city, price, date) in _ROWS.items()
        ],
    )
    await client.create_payload_index(
        name, field_name="price", field_schema=PayloadSchemaType.FLOAT
    )
    await client.create_payload_index(
        name, field_name="date", field_schema=PayloadSchemaType.DATETIME
    )
    try:
        yield server, name
    finally:
        await client.delete_collection(name)
        await client.close()


async def _call(server: MCPServer[None], tool: str, **args: Any) -> dict[str, Any]:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    content: dict[str, Any] | None = result.structured_content
    assert content is not None
    return content


def _ids(content: dict[str, Any]) -> list[int]:
    return [p["id"] for p in content["points"]]


async def _query(server: MCPServer[None], name: str, **args: Any) -> dict[str, Any]:
    return await _call(server, "qdrant_query", collection_name=name, **args)


# --- tuning ---------------------------------------------------------------------


async def test_tuning_parameters_change_the_result_as_documented(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    base = {"query_vector": _DENSE_QUERY, "using": "dense", "limit": 5}

    plain = _ids(await _query(server, name, **base))
    assert set(plain[:3]) == {1, 2, 3} and plain[3:] == [5, 4]

    exact = await _query(
        server,
        name,
        **base,
        search_params={
            "exact": True,
            "hnsw_ef": 64,
            "quantization": {"ignore": True},
            "acorn": {"enable": True},
        },
    )
    assert _ids(exact) == plain  # exact search agrees with the index on a tiny collection

    assert set(_ids(await _query(server, name, **base, score_threshold=0.999))) == {1, 2, 3}
    assert _ids(await _query(server, name, **base, offset=3)) == plain[3:]
    assert _ids(await _query(server, name, **base, timeout_seconds=5)) == plain
    assert _ids(await _query(server, name, **base, consistency=1)) == plain
    assert _ids(await _query(server, name, **base, consistency="majority")) == plain


# --- modes -----------------------------------------------------------------------


async def test_mmr_promotes_the_dissimilar_point(env: tuple[MCPServer[None], str]) -> None:
    server, name = env
    base = {"query_vector": _DENSE_QUERY, "using": "dense", "limit": 5}

    plain = _ids(await _query(server, name, **base))
    diverse = _ids(
        await _query(server, name, **base, mmr={"diversity": 0.9, "candidates_limit": 10})
    )

    assert plain[-1] == 4  # the orthogonal point is the least similar...
    assert diverse.index(4) < plain.index(4)  # ...and MMR moves it up
    assert set(diverse) == set(plain)
    assert _ids(await _query(server, name, **base, mmr={})) != []  # Qdrant's defaults work


async def test_mmr_needs_candidates_beyond_limit_and_offset_pages_inside_the_limit(
    env: tuple[MCPServer[None], str],
) -> None:
    """Pins the two MMR facts the `qdrant_query` docstring warns about."""
    server, name = env
    base = {"query_vector": _DENSE_QUERY, "using": "dense"}

    plain_top2 = _ids(await _query(server, name, **base, limit=2))
    no_candidates = _ids(await _query(server, name, **base, limit=2, mmr={"diversity": 0.9}))
    wide = _ids(
        await _query(server, name, **base, limit=2, mmr={"diversity": 0.9, "candidates_limit": 10})
    )
    assert no_candidates == plain_top2  # candidates_limit defaults to limit: nothing to choose from
    assert 4 in wide and 4 not in no_candidates

    mmr = {"diversity": 0.9, "candidates_limit": 10}
    assert len(_ids(await _query(server, name, **base, limit=2, mmr=mmr, offset=1))) == 1
    assert _ids(await _query(server, name, **base, limit=2, mmr=mmr, offset=2)) == []


async def test_formula_rescores_a_prefetch_with_a_payload_boost(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    prefetch = [{"query_vector": _DENSE_QUERY, "using": "dense", "limit": 5}]

    boosted = await _query(
        server,
        name,
        prefetch=prefetch,
        formula={
            "expression": {
                "sum": ["$score", {"mult": [0.5, {"key": "city", "match": {"value": "sf"}}]}]
            }
        },
    )
    scores = {p["id"]: p["score"] for p in boosted["points"]}
    assert _ids(boosted)[0] == 3  # a sf near-duplicate now beats the ny ones
    assert scores[3] == pytest.approx(scores[1] + 0.5, abs=0.01)

    decayed = await _query(
        server,
        name,
        prefetch=prefetch,
        formula={
            "expression": {
                "sum": [
                    "$score",
                    {
                        "exp_decay": {
                            "x": {"datetime_key": "date"},
                            "target": {"datetime": "2026-01-03T00:00:00Z"},
                            "scale": 2592000,
                            "midpoint": 0.5,
                        }
                    },
                ]
            }
        },
    )
    assert _ids(decayed)[0] == 3  # the most recent near-duplicate wins
    assert _ids(decayed)[-1] == 4  # the oldest, least similar one is last


async def test_formula_error_cases_surface_qdrants_own_message(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env
    prefetch = [{"query_vector": _DENSE_QUERY, "using": "dense", "limit": 5}]
    boost = {"sum": ["$score", "popularity"]}

    with pytest.raises(ToolError, match="without prefetches"):
        await _query(server, name, formula={"expression": "$score"})

    with pytest.raises(ToolError, match="popularity"):
        await _query(server, name, prefetch=prefetch, formula={"expression": boost})

    with_defaults = await _query(
        server,
        name,
        prefetch=prefetch,
        formula={"expression": boost, "defaults": {"popularity": 0}},
    )
    assert len(_ids(with_defaults)) == 5


async def test_order_by_sorts_by_a_payload_field_and_start_from_pages(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env

    assert _ids(
        await _query(server, name, order_by={"key": "price", "direction": "desc"}, limit=3)
    ) == [5, 4, 3]
    assert _ids(await _query(server, name, order_by="price", limit=2)) == [1, 2]
    from_25 = {"key": "price", "direction": "asc", "start_from": 25}
    assert _ids(await _query(server, name, order_by=from_25, limit=5)) == [3, 4, 5]

    with pytest.raises(ToolError, match="No range index"):
        await _query(server, name, order_by="city")


async def test_sample_random_returns_distinct_points(env: tuple[MCPServer[None], str]) -> None:
    server, name = env

    ids = _ids(await _query(server, name, sample="random", limit=3))

    assert len(ids) == 3 and len(set(ids)) == 3 and set(ids) <= set(_ROWS)


async def test_rrf_weights_follow_the_order_of_the_prefetch_stages(
    env: tuple[MCPServer[None], str],
) -> None:
    """Stage A can only return point 1 and stage B only point 2, so the weight
    that is larger decides the winner with no score ties involved."""
    server, name = env
    stages = [
        {
            "query_vector": _DENSE_QUERY,
            "using": "dense",
            "limit": 1,
            "query_filter": {"must": [{"has_id": [1]}]},
        },
        {
            "query_vector": _DENSE_QUERY,
            "using": "dense",
            "limit": 1,
            "query_filter": {"must": [{"has_id": [2]}]},
        },
    ]

    first = await _query(
        server, name, prefetch=stages, fusion={"method": "rrf", "weights": [10, 1]}, limit=2
    )
    second = await _query(
        server, name, prefetch=stages, fusion={"method": "rrf", "weights": [1, 10]}, limit=2
    )
    assert _ids(first) == [1, 2]
    assert _ids(second) == [2, 1]

    with pytest.raises(ToolError, match="does not match number of prefetches"):
        await _query(server, name, prefetch=stages, fusion={"method": "rrf", "weights": [1]})


async def test_nested_prefetch_fuses_dense_and_sparse_then_reranks_with_a_multivector(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env

    result = await _query(
        server,
        name,
        query_vector=[[0.0, 1.0]],
        using="colbert",
        prefetch=[
            {
                "fusion": "rrf",
                "limit": 5,
                "prefetch": [
                    {"query_vector": _DENSE_QUERY, "using": "dense", "limit": 3},
                    {
                        "query_vector": {"indices": [1], "values": [1.0]},
                        "using": "sparse",
                        "limit": 3,
                    },
                ],
            }
        ],
        limit=3,
    )

    ids = _ids(result)
    assert ids[0] == 4  # the multivector rerank puts the point closest to [0, 1] first
    assert len(ids) == 3


async def test_recommend_and_discover_take_the_same_tuning(
    env: tuple[MCPServer[None], str],
) -> None:
    server, name = env

    recommended = await _call(
        server,
        "qdrant_recommend",
        collection_name=name,
        positive=[1],
        using="dense",
        score_threshold=0.9,
        search_params={"exact": True},
    )
    assert 4 not in _ids(recommended)  # below the threshold
    assert 3 in _ids(recommended)

    everything = _ids(
        await _call(server, "qdrant_recommend", collection_name=name, positive=[1], using="dense")
    )
    paged = _ids(
        await _call(
            server, "qdrant_recommend", collection_name=name, positive=[1], using="dense", offset=2
        )
    )
    assert paged == everything[2:]

    discovered = await _call(
        server,
        "qdrant_discover",
        collection_name=name,
        target=1,
        context=[{"positive": 2, "negative": 4}],
        using="dense",
        offset=1,
        timeout_seconds=5,
    )
    everything_discovered = _ids(
        await _call(
            server,
            "qdrant_discover",
            collection_name=name,
            target=1,
            context=[{"positive": 2, "negative": 4}],
            using="dense",
        )
    )
    assert len(everything_discovered) == 2  # target and context points are excluded
    assert _ids(discovered) == everything_discovered[1:]


async def test_batch_and_groups_accept_the_new_modes(env: tuple[MCPServer[None], str]) -> None:
    server, name = env

    batch = await _call(
        server,
        "qdrant_query_batch",
        collection_name=name,
        queries=[
            {"order_by": "price", "limit": 2},
            {"sample": "random", "limit": 2},
            {"query_vector": _DENSE_QUERY, "using": "dense", "mmr": {"diversity": 0.5}, "limit": 2},
        ],
        timeout_seconds=5,
        consistency="majority",
    )
    results = batch["result"]
    assert [len(r["points"]) for r in results] == [2, 2, 2]
    assert [p["id"] for p in results[0]["points"]] == [1, 2]

    groups = await _call(
        server,
        "qdrant_query_groups",
        collection_name=name,
        group_by="city",
        query_vector=_DENSE_QUERY,
        using="dense",
        group_size=2,
        score_threshold=0.5,
    )
    assert {g["id"] for g in groups["groups"]} == {"ny", "sf"}


# --- scroll ------------------------------------------------------------------------


async def test_scroll_order_by_and_its_paging_rules(env: tuple[MCPServer[None], str]) -> None:
    server, name = env

    ascending = await _call(
        server, "qdrant_points_scroll", collection_name=name, order_by="price", limit=3
    )
    assert [p["id"] for p in ascending["points"]] == [1, 2, 3]
    assert ascending["next_page_offset"] is None  # `null` does NOT mean "no more" here

    descending = await _call(
        server,
        "qdrant_points_scroll",
        collection_name=name,
        order_by={"key": "price", "direction": "desc"},
        limit=3,
    )
    assert [p["id"] for p in descending["points"]] == [5, 4, 3]

    # The documented way to continue: start_from = the last value received.
    last_price = ascending["points"][-1]["payload"]["price"]
    next_page = await _call(
        server,
        "qdrant_points_scroll",
        collection_name=name,
        order_by={"key": "price", "direction": "asc", "start_from": last_price},
        limit=3,
    )
    assert [p["id"] for p in next_page["points"]] == [3, 4, 5]  # 3 repeats: ties on start_from

    with pytest.raises(ToolError, match="offset"):
        await _call(
            server, "qdrant_points_scroll", collection_name=name, order_by="price", offset=1
        )
