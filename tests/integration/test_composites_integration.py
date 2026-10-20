"""Confirms `qdrant_collection_copy` and `qdrant_payload_schema_infer` work
against a real Qdrant — vectors of every kind survive a copy, a copy can be
resumed page by page, and the reindex flow (copy + alias switch) behaves as the
tool docstrings describe."""

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

from mcp_qdrant.tools import admin as admin_tools
from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools import composites as composites_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

_POINT_COUNT = 7


def _vectors_config() -> dict[str, Any]:
    return {
        "vectors_config": {
            "dense": VectorParams(size=4, distance=Distance.COSINE),
            "colbert": VectorParams(
                size=2,
                distance=Distance.COSINE,
                multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM),
            ),
        },
        "sparse_vectors_config": {"sparse": SparseVectorParams()},
    }


def _points() -> list[PointStruct]:
    return [
        PointStruct(
            id=i,
            vector={
                "dense": [1.0, 0.0, 0.0, float(i)],
                "sparse": SparseVector(indices=[1, 2], values=[1.0, float(i)]),
                "colbert": [[1.0, 0.0], [0.0, float(i)]],
            },
            payload={"n": i, "city": "ny" if i % 2 else "sf"},
        )
        for i in range(1, _POINT_COUNT + 1)
    ]


@pytest.fixture
async def env() -> AsyncIterator[tuple[MCPServer[None], AsyncQdrantClient, str]]:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    suffix = uuid.uuid4().hex[:8]

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "admin"), read_only=False)
    collections_tools.register(registry, client)
    admin_tools.register(registry, client)
    composites_tools.register(registry, client)

    try:
        yield server, client, suffix
    finally:
        for prefix in ("src", "dst", "schema"):
            await client.delete_collection(f"mcp-test-{prefix}-{suffix}")  # no-op if absent
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> dict[str, Any]:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    content: dict[str, Any] | None = result.structured_content
    assert content is not None
    return content


async def _seed_source(client: AsyncQdrantClient, name: str) -> None:
    await client.create_collection(name, **_vectors_config())
    await client.upsert(name, points=_points())


async def _copy_everything(
    server: MCPServer[None], source: str, target: str, **args: Any
) -> list[dict[str, Any]]:
    """Drive the copy the way an LLM would: repeat with `offset=next_offset`
    until `done`. Returns every call's result."""
    calls: list[dict[str, Any]] = []
    offset: int | str | None = None
    while True:
        result = await _call(
            server,
            "qdrant_collection_copy",
            {"source_collection": source, "target_collection": target, "offset": offset, **args},
        )
        calls.append(result)
        if result["done"]:
            return calls
        offset = result["next_offset"]
        assert len(calls) < 20, "copy never reported done"


async def test_copy_is_resumable_and_preserves_dense_sparse_and_multivectors(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    src, dst = f"mcp-test-src-{suffix}", f"mcp-test-dst-{suffix}"
    await _seed_source(client, src)
    await client.create_collection(dst, **_vectors_config())

    calls = await _copy_everything(server, src, dst, batch_size=2, max_points=3)

    # 7 points, at most 3 per call: 3 + 3 + 1, only the last call reports done.
    assert [c["copied"] for c in calls] == [3, 3, 1]
    assert [c["done"] for c in calls] == [False, False, True]
    assert (await client.count(dst)).count == _POINT_COUNT

    source_points = {
        p.id: p for p in await client.retrieve(src, ids=list(range(1, 8)), with_vectors=True)
    }
    target_points = {
        p.id: p for p in await client.retrieve(dst, ids=list(range(1, 8)), with_vectors=True)
    }
    assert target_points.keys() == source_points.keys()
    for point_id, expected in source_points.items():
        assert target_points[point_id].payload == expected.payload
        assert target_points[point_id].vector == expected.vector  # dense + sparse + colbert


async def test_copy_is_idempotent_when_run_again(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    src, dst = f"mcp-test-src-{suffix}", f"mcp-test-dst-{suffix}"
    await _seed_source(client, src)
    await client.create_collection(dst, **_vectors_config())

    await _copy_everything(server, src, dst)
    await _copy_everything(server, src, dst)

    assert (await client.count(dst)).count == _POINT_COUNT


async def test_copy_filter_copies_only_matching_points(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    src, dst = f"mcp-test-src-{suffix}", f"mcp-test-dst-{suffix}"
    await _seed_source(client, src)
    await client.create_collection(dst, **_vectors_config())

    calls = await _copy_everything(
        server, src, dst, copy_filter={"must": [{"key": "city", "match": {"value": "ny"}}]}
    )

    assert sum(c["copied"] for c in calls) == 4  # ids 1, 3, 5, 7
    cities = {p.payload["city"] for p in (await client.scroll(dst, limit=20))[0] if p.payload}
    assert cities == {"ny"}


async def test_copy_refuses_a_missing_target_and_copying_onto_itself_via_an_alias(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    src = f"mcp-test-src-{suffix}"
    await _seed_source(client, src)

    with pytest.raises(ToolError, match="create it first"):
        await server.call_tool(
            "qdrant_collection_copy",
            {"source_collection": src, "target_collection": f"mcp-test-dst-{suffix}"},
        )

    alias = f"mcp-test-alias-{suffix}"
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": src, "alias_name": alias}}]},
    )
    with pytest.raises(ToolError, match="same collection"):
        await server.call_tool(
            "qdrant_collection_copy", {"source_collection": alias, "target_collection": src}
        )


async def test_copy_into_an_incompatible_target_reports_where_to_resume(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    src, dst = f"mcp-test-src-{suffix}", f"mcp-test-dst-{suffix}"
    await _seed_source(client, src)
    await client.create_collection(dst, vectors_config=VectorParams(size=3, distance=Distance.DOT))

    with pytest.raises(ToolError) as excinfo:
        await server.call_tool(
            "qdrant_collection_copy", {"source_collection": src, "target_collection": dst}
        )

    assert "Copy stopped after 0 points; resume with offset=None" in str(excinfo.value)
    assert (await client.count(dst)).count == 0


async def test_reindex_with_a_new_distance_then_switch_the_alias(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    """The use case the tools exist for: Qdrant can't change a collection's
    distance in place, so build a new one, copy into it, and repoint the alias
    the clients use."""
    server, client, suffix = env
    src, dst, alias = (
        f"mcp-test-src-{suffix}",
        f"mcp-test-dst-{suffix}",
        f"mcp-test-live-{suffix}",
    )
    await client.create_collection(
        src, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    await client.upsert(src, points=[PointStruct(id=i, vector=[1.0, float(i)]) for i in (1, 2, 3)])
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": src, "alias_name": alias}}]},
    )

    await _call(
        server,
        "qdrant_collection_create",
        {"collection_name": dst, "vector_size": 2, "distance": "Euclid"},
    )
    await _copy_everything(server, alias, dst)  # the source can be named through its alias
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": dst, "alias_name": alias}}]},
    )

    via_alias = await client.get_collection(alias)
    assert via_alias.config.params.vectors.distance == Distance.EUCLID  # type: ignore[union-attr]
    assert (await client.count(alias)).count == 3


async def test_schema_infer_profiles_real_payloads_and_facets_indexed_keys(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    _, client, suffix = env
    name = f"mcp-test-schema-{suffix}"
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("admin",), read_only=False)
    composites_tools.register(registry, client)

    await client.create_collection(name, **_vectors_config())
    await client.upsert(
        name,
        points=[
            PointStruct(
                id=i,
                vector={
                    "dense": [1.0, 0.0, 0.0, 0.0],
                    "sparse": SparseVector(indices=[1], values=[1.0]),
                    "colbert": [[1.0, 0.0]],
                },
                payload={
                    "city": "ny" if i <= 4 else "sf",
                    "price": i * 1.5,
                    "active": i % 2 == 0,
                    "when": "2026-01-01T00:00:00Z",
                    "tags": ["a", "b"],
                    "meta": {"owner": "x", "deep": {"k": i}},
                    "items": [{"sku": f"s{i}", "qty": 2}],
                    **({"rare": "only-once"} if i == 1 else {}),
                },
            )
            for i in range(1, 7)
        ],
    )
    for key, schema in (
        ("city", PayloadSchemaType.KEYWORD),
        ("price", PayloadSchemaType.FLOAT),
        ("active", PayloadSchemaType.BOOL),
        ("meta.deep.k", PayloadSchemaType.INTEGER),
        ("items[].sku", PayloadSchemaType.KEYWORD),
        ("gone", PayloadSchemaType.KEYWORD),
    ):
        await client.create_payload_index(name, field_name=key, field_schema=schema)

    profile = await _call(server, "qdrant_payload_schema_infer", {"collection_name": name})

    assert profile["sampled"] == 6  # the sample covers the whole (tiny) collection
    assert profile["collection_points"] == 6
    fields = {f["key"]: f for f in profile["fields"]}
    assert set(fields) == {
        "city", "price", "active", "when", "tags", "meta.owner", "meta.deep.k",
        "items[].sku", "items[].qty", "rare",
    }  # fmt: skip

    assert fields["city"]["types"] == ["string"]
    assert fields["city"]["index_type"] == "keyword"
    assert {(v["value"], v["count"]) for v in fields["city"]["top_values"]} == {
        ("ny", 4),
        ("sf", 2),
    }
    assert fields["price"]["types"] == ["float"]
    assert fields["price"]["top_values"] is None  # Qdrant can't facet a float index
    assert {(v["value"], v["count"]) for v in fields["active"]["top_values"]} == {
        (True, 3),
        (False, 3),
    }
    assert fields["when"]["indexed"] is False
    assert fields["tags"]["is_array"] is True and fields["tags"]["types"] == ["string"]
    assert fields["meta.deep.k"]["index_type"] == "integer"
    assert fields["items[].sku"]["index_type"] == "keyword"
    assert fields["rare"]["present_in"] == 1
    assert fields["city"]["present_in"] == 6
    assert profile["indexed_but_unseen"] == ["gone"]
    assert profile["fields_truncated"] is False

    capped = await _call(
        server, "qdrant_payload_schema_infer", {"collection_name": name, "max_fields": 3}
    )
    assert len(capped["fields"]) == 3
    assert capped["fields_truncated"] is True

    no_facets = await _call(
        server, "qdrant_payload_schema_infer", {"collection_name": name, "top_values": 0}
    )
    assert all(f["top_values"] is None for f in no_facets["fields"])
