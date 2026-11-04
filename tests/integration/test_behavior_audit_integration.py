"""Real-Qdrant checks pinning the tool descriptions corrected by the Fase 17b audit:
behavioral claims from before Fase 12 that an independent reviewer found false (and I
re-reproduced) on Qdrant 1.20. If one of these fails after a Qdrant upgrade, update the
description it pins, don't silence the test."""

from __future__ import annotations

import io
import json
import os
import tarfile
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CreateAlias,
    CreateAliasOperation,
    Distance,
    OptimizersConfigDiff,
    PayloadSchemaType,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server

pytestmark = pytest.mark.integration

URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
Env = tuple[MCPServer[None], AsyncQdrantClient, str]


@pytest.fixture
async def env() -> AsyncIterator[Env]:
    client = AsyncQdrantClient(url=URL, timeout=30)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    server = build_server(Settings(qdrant_url=URL, toolsets=ALL_TOOLSETS))
    await client.create_collection(
        name,
        vectors_config=VectorParams(size=2, distance=Distance.COSINE),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=1111),
    )
    await client.upsert(
        name,
        points=[PointStruct(id=i, vector=[1.0, i * 0.1], payload={"n": i}) for i in (1, 2, 3, 4)],
        wait=True,
    )
    try:
        yield server, client, name
    finally:
        for collection in (name, f"{name}-fresh"):
            if await client.collection_exists(collection):
                for snapshot in await client.list_snapshots(collection):
                    await client.delete_snapshot(collection, snapshot.name)
                await client.delete_collection(collection)
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> Any:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return result.structured_content


async def test_quotas_set_replaces_the_whole_config(env: Env) -> None:
    server, _, _ = env
    try:
        await _call(server, "qdrant_quotas_set", {"enabled": True, "max_disk_usage_percent": 99})
        await _call(server, "qdrant_quotas_set", {"max_disk_usage_percent": 99})
        config = (await _call(server, "qdrant_quotas_get", {}))["config"]
        assert config["enabled"] is False  # omitted → reset, not kept
        assert config["max_disk_usage_percent"] == 99
    finally:
        await _call(server, "qdrant_quotas_set", {})


async def test_deleting_a_missing_snapshot_is_an_error(env: Env) -> None:
    server, _, name = env
    snapshot = await _call(server, "qdrant_snapshot_create", {"collection_name": name})
    args = {"collection_name": name, "snapshot_name": snapshot["name"]}
    assert (await _call(server, "qdrant_snapshot_delete", args))["deleted"] is True
    with pytest.raises(ToolError, match="not found"):
        await server.call_tool("qdrant_snapshot_delete", args)
    with pytest.raises(ToolError, match="not found"):
        await server.call_tool("qdrant_storage_snapshot_delete", {"snapshot_name": "nope.snapshot"})


async def test_negative_only_recommend_needs_a_non_average_strategy(env: Env) -> None:
    server, _, name = env
    with pytest.raises(ToolError, match="Positive vectors should not be empty"):
        await server.call_tool("qdrant_recommend", {"collection_name": name, "negative": [1]})
    result = await _call(
        server,
        "qdrant_recommend",
        {"collection_name": name, "negative": [1], "strategy": "best_score"},
    )
    assert result["points"]


async def test_snapshot_recover_restores_points_but_keeps_config_indexes_and_aliases(
    env: Env,
) -> None:
    server, client, name = env
    snapshot = await _call(server, "qdrant_snapshot_create", {"collection_name": name})
    location = f"{URL}/collections/{name}/snapshots/{snapshot['name']}"

    await client.upsert(name, [PointStruct(id=9, vector=[0.0, 1.0])], wait=True)
    await client.create_payload_index(name, "v", PayloadSchemaType.KEYWORD, wait=True)
    await client.update_collection(
        name, optimizers_config=OptimizersConfigDiff(indexing_threshold=2222)
    )
    alias = f"{name}-alias"
    await client.update_collection_aliases(
        [CreateAliasOperation(create_alias=CreateAlias(collection_name=name, alias_name=alias))]
    )
    try:
        await _call(
            server, "qdrant_snapshot_recover", {"collection_name": name, "location": location}
        )
        info = await client.get_collection(name)
        assert (await client.count(name)).count == 4  # point 9 is gone
        assert "v" in info.payload_schema  # the index created after the snapshot stays
        assert info.config.optimizer_config.indexing_threshold == 2222  # config not rolled back
        assert alias in {a.alias_name for a in (await client.get_collection_aliases(name)).aliases}

        fresh = f"{name}-fresh"
        await _call(
            server, "qdrant_snapshot_recover", {"collection_name": fresh, "location": location}
        )
        fresh_info = await client.get_collection(fresh)
        assert fresh_info.payload_schema == {}
        assert fresh_info.config.optimizer_config.indexing_threshold == 1111
    finally:
        await client.delete_collection(name)  # also drops the alias


async def test_storage_snapshot_holds_collections_and_aliases_only(env: Env) -> None:
    server, _, _ = env
    snapshot = await _call(server, "qdrant_storage_snapshot_create", {})
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            raw = (await http.get(f"{URL}/snapshots/{snapshot['name']}")).content
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            names = archive.getnames()
            assert names.count("config.json") == 1
            assert all(n == "config.json" or n.endswith(".snapshot") for n in names)
            member = archive.extractfile("config.json")
            assert member is not None
            assert set(json.loads(member.read())) == {"collections_mapping", "collections_aliases"}
    finally:
        await _call(server, "qdrant_storage_snapshot_delete", {"snapshot_name": snapshot["name"]})


async def test_telemetry_details_need_a_details_level(env: Env) -> None:
    server, _, _ = env
    default = await _call(server, "qdrant_telemetry", {})
    assert default["memory"] is None and default["hardware"] is None
    assert default["collections"]["collections"] is None
    detailed = await _call(server, "qdrant_telemetry", {"details_level": 1})
    assert detailed["memory"] is not None and detailed["hardware"] is not None
    assert detailed["collections"]["collections"]


async def test_payload_index_create_replaces_an_index_with_another_schema(env: Env) -> None:
    server, client, name = env
    await client.create_payload_index(name, "n", PayloadSchemaType.INTEGER, wait=True)
    await _call(
        server,
        "qdrant_payload_index_create",
        {"collection_name": name, "field_name": "n", "field_schema": "keyword"},
    )
    info = await client.get_collection(name)
    assert info.payload_schema["n"].data_type == PayloadSchemaType.KEYWORD


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("qdrant_payload_set", {"payload": {"q": 1}, "ids": [999, 3]}),
        ("qdrant_payload_overwrite", {"payload": {"q": 1}, "ids": [999, 3]}),
        ("qdrant_payload_delete", {"keys": ["n"], "ids": [999, 3]}),
        ("qdrant_payload_clear", {"ids": [999, 3]}),
        (
            "qdrant_vectors_update",
            {"points": [{"id": 999, "vector": [0.0, 1.0]}, {"id": 3, "vector": [0.0, 1.0]}]},
        ),
    ],
)
async def test_an_unknown_id_fails_the_call_but_existing_ids_are_still_written(
    env: Env, tool: str, args: dict[str, Any]
) -> None:
    server, client, name = env
    before = (await client.retrieve(name, [3], with_vectors=True))[0]
    with pytest.raises(ToolError, match="No point with id 999 found"):
        await server.call_tool(tool, {"collection_name": name, **args})
    after = (await client.retrieve(name, [3], with_vectors=True))[0]
    assert (after.payload, after.vector) != (before.payload, before.vector)


async def test_query_by_point_id_leaves_that_point_out(env: Env) -> None:
    server, _, name = env
    result = await _call(server, "qdrant_query", {"collection_name": name, "query_vector": 1})
    ids = [p["id"] for p in result["points"]]
    assert 1 not in ids and set(ids) == {2, 3, 4}


async def test_upsert_with_update_filter_still_inserts_new_ids(env: Env) -> None:
    server, client, name = env
    await _call(
        server,
        "qdrant_points_upsert",
        {
            "collection_name": name,
            "points": [{"id": 50, "vector": [1.0, 0.0]}],
            "update_filter": {"must": [{"key": "n", "match": {"value": 12345}}]},
        },
    )
    assert len(await client.retrieve(name, [50])) == 1


async def test_facet_needs_a_payload_index(env: Env) -> None:
    server, _, name = env
    with pytest.raises(ToolError, match="No appropriate index for faceting"):
        await server.call_tool("qdrant_payload_facet", {"collection_name": name, "key": "n"})


async def test_vectors_delete_with_an_unknown_id_still_deletes_from_existing_ids(env: Env) -> None:
    server, client, name = env
    named = f"{name}-fresh"  # cleaned up by the fixture
    await client.create_collection(
        named,
        vectors_config={"dense": VectorParams(size=2, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )
    point = PointStruct(
        id=3, vector={"dense": [1.0, 0.0], "sparse": SparseVector(indices=[1], values=[1.0])}
    )
    await client.upsert(named, [point], wait=True)
    with pytest.raises(ToolError, match="No point with id 999 found"):
        await server.call_tool(
            "qdrant_vectors_delete",
            {"collection_name": named, "vector_names": ["sparse"], "ids": [999, 3]},
        )
    stored = (await client.retrieve(named, [3], with_vectors=True))[0].vector
    assert isinstance(stored, dict) and set(stored) == {"dense"}
