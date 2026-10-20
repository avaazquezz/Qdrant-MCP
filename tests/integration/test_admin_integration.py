"""Confirms the `admin` toolset (aliases, shard layout, optimizer progress) and
the new `qdrant_collection_create` options work against a real single-node
Qdrant — including the behaviors the tool docstrings promise."""

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
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.tools import admin as admin_tools
from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


@pytest.fixture
async def env() -> AsyncIterator[tuple[MCPServer[None], AsyncQdrantClient, str]]:
    """A server with `core` + `admin`, and a unique suffix for this test's names."""
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    suffix = uuid.uuid4().hex[:8]

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "admin"), read_only=False)
    collections_tools.register(registry, client)
    points_tools.register(registry, client)
    admin_tools.register(registry, client)

    try:
        yield server, client, suffix
    finally:
        for name in [f"mcp-test-a-{suffix}", f"mcp-test-b-{suffix}", f"mcp-test-c-{suffix}"]:
            await client.delete_collection(name)  # a no-op when it was never created
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> CallToolResult:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    return result


async def _make_collection(client: AsyncQdrantClient, name: str, marker: str) -> None:
    await client.create_collection(
        name, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    await client.upsert(name, points=[PointStruct(id=1, vector=[1.0, 0.0], payload={"in": marker})])


def _aliases(result: CallToolResult) -> dict[str, str]:
    assert result.structured_content is not None
    return {a["alias_name"]: a["collection_name"] for a in result.structured_content["aliases"]}


async def _payload_via(server: MCPServer[None], name: str) -> dict[str, Any]:
    result = await _call(server, "qdrant_points_get", {"collection_name": name, "ids": [1]})
    assert result.structured_content is not None
    payload: dict[str, Any] = result.structured_content["points"][0]["payload"]
    return payload


async def test_alias_lifecycle_and_zero_downtime_switch(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    a, b, alias = f"mcp-test-a-{suffix}", f"mcp-test-b-{suffix}", f"mcp-test-live-{suffix}"
    await _make_collection(client, a, "A")
    await _make_collection(client, b, "B")

    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": a, "alias_name": alias}}]},
    )
    assert _aliases(await _call(server, "qdrant_alias_list", {}))[alias] == a
    assert _aliases(await _call(server, "qdrant_collection_aliases", {"collection_name": a})) == {
        alias: a
    }
    assert (await _payload_via(server, alias)) == {"in": "A"}  # an alias works as a collection name

    # Switching consumers to the new collection: one create_alias re-points it.
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": b, "alias_name": alias}}]},
    )
    assert (await _payload_via(server, alias)) == {"in": "B"}
    assert (
        await _call(server, "qdrant_collection_aliases", {"collection_name": a})
    ).structured_content == {"aliases": []}

    await _call(
        server,
        "qdrant_alias_update",
        {
            "operations": [
                {"rename_alias": {"old_alias_name": alias, "new_alias_name": alias + "-r"}}
            ]
        },
    )
    assert _aliases(await _call(server, "qdrant_alias_list", {}))[alias + "-r"] == b
    assert alias not in _aliases(await _call(server, "qdrant_alias_list", {}))

    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"delete_alias": {"alias_name": alias + "-r"}}]},
    )
    assert alias + "-r" not in _aliases(await _call(server, "qdrant_alias_list", {}))


async def test_alias_update_edge_behaviors_documented_in_the_tool(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    a, b = f"mcp-test-a-{suffix}", f"mcp-test-b-{suffix}"
    await _make_collection(client, a, "A")
    await _make_collection(client, b, "B")

    # Deleting an alias that doesn't exist is a no-op, not an error.
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"delete_alias": {"alias_name": f"ghost-{suffix}"}}]},
    )

    # An alias can't take the name of an existing collection.
    with pytest.raises(ToolError, match="already exists"):
        await server.call_tool(
            "qdrant_alias_update",
            {"operations": [{"create_alias": {"collection_name": a, "alias_name": b}}]},
        )

    # Creating an alias for a missing collection fails with Qdrant's own message.
    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_alias_update",
            {
                "operations": [
                    {"create_alias": {"collection_name": f"nope-{suffix}", "alias_name": "x"}}
                ]
            },
        )

    # Deleting a collection removes the aliases that pointed to it.
    alias = f"mcp-test-gone-{suffix}"
    await _call(
        server,
        "qdrant_alias_update",
        {"operations": [{"create_alias": {"collection_name": b, "alias_name": alias}}]},
    )
    await client.delete_collection(b)
    assert alias not in _aliases(await _call(server, "qdrant_alias_list", {}))


async def test_alias_batch_is_not_rolled_back_when_a_later_operation_fails(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    """Pins the behavior the `qdrant_alias_update` docstring warns about. If a
    future Qdrant makes batches all-or-nothing, this fails and the docstring
    (plus the ROADMAP finding) should be updated, not this test silenced."""
    server, client, suffix = env
    a = f"mcp-test-a-{suffix}"
    await _make_collection(client, a, "A")
    first = f"mcp-test-first-{suffix}"

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_alias_update",
            {
                "operations": [
                    {"create_alias": {"collection_name": a, "alias_name": first}},
                    {"create_alias": {"collection_name": f"nope-{suffix}", "alias_name": "x"}},
                ]
            },
        )

    assert first in _aliases(await _call(server, "qdrant_alias_list", {}))
    await _call(
        server, "qdrant_alias_update", {"operations": [{"delete_alias": {"alias_name": first}}]}
    )


async def test_collection_cluster_info_on_a_single_node(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    a = f"mcp-test-a-{suffix}"
    await _make_collection(client, a, "A")

    info = (
        await _call(server, "qdrant_collection_cluster_info", {"collection_name": a})
    ).structured_content
    assert info is not None
    assert info["shard_count"] == 1
    assert info["remote_shards"] == []
    assert [s["points_count"] for s in info["local_shards"]] == [1]

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_collection_cluster_info", {"collection_name": f"nope-{suffix}"}
        )


async def test_collection_optimizations_summary_and_detail_lists(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, suffix = env
    a = f"mcp-test-a-{suffix}"
    await _make_collection(client, a, "A")

    plain = (
        await _call(server, "qdrant_collection_optimizations", {"collection_name": a})
    ).structured_content
    assert plain is not None
    assert set(plain["summary"]) >= {"queued_optimizations", "queued_segments", "idle_segments"}
    assert plain["running"] == []
    # Without `include`, the detail lists are not requested.
    assert plain["queued"] is None and plain["completed"] is None and plain["idle_segments"] is None

    detailed = (
        await _call(
            server,
            "qdrant_collection_optimizations",
            {
                "collection_name": a,
                "include": ["queued", "completed", "idle_segments"],
                "completed_limit": 5,
            },
        )
    ).structured_content
    assert detailed is not None
    assert isinstance(detailed["queued"], list)
    assert isinstance(detailed["completed"], list)
    assert isinstance(detailed["idle_segments"], list)

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_collection_optimizations", {"collection_name": f"nope-{suffix}"}
        )


async def test_collection_create_applies_hnsw_optimizers_and_on_disk_payload(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, _, suffix = env
    name = f"mcp-test-c-{suffix}"

    created = (
        await _call(
            server,
            "qdrant_collection_create",
            {
                "collection_name": name,
                "vector_size": 2,
                "hnsw_config": {"m": 0, "payload_m": 16},
                "optimizers_config": {"indexing_threshold": 5000},
                "on_disk_payload": True,
            },
        )
    ).structured_content
    assert created is not None
    config = created["config"]
    assert config["hnsw_config"]["m"] == 0
    assert config["hnsw_config"]["payload_m"] == 16
    assert config["optimizer_config"]["indexing_threshold"] == 5000
    assert config["params"]["on_disk_payload"] is True
